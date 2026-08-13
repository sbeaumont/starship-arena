"""A game written out as text, which is what is left of it once the pickles no longer read."""
import json
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase

from jsonschema import ValidationError

from arena.app import valhalla
from arena.app.services import AdminService, GameService

# Twenty apart and pointed at each other, so every rocket goes off in the round it was fired.
DUEL = [{'name': 'Alpha', 'type': 'H2545', 'faction': 'One', 'player': 'Menno', 'x': 0, 'y': -20},
        {'name': 'Beta', 'type': 'A2527', 'faction': 'Two', 'player': 'Rik', 'x': 0, 'y': 20}]

EXAMPLE = Path(__file__).parent / 'valhalla-v1-example.json'


class TestExportingToValhalla(TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.admin = AdminService(str(self.root))
        self.game = GameService(str(self.root))
        self.admin.create_game('duel', DUEL, 'generic')
        self.game.save_commands('duel', 'Alpha',
                                [f'{t}: Fire R1 0' for t in range(1, 6)] + ['1: Fire L1 Beta'])
        self.game.save_commands('duel', 'Beta', [])
        self.admin.process_turn('duel')
        self.where = Path(self.admin.export_to_valhalla('duel'))
        self.exported = valhalla.load((self.where / 'replay.json').read_text())

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def named(self, name):
        return next(o for o in self.exported['objects'] if o['name'] == name)

    def test_it_lands_in_the_museum_and_leaves_the_game_where_it_was(self):
        self.assertEqual(self.root / 'valhalla' / 'duel', self.where)
        self.assertTrue((self.root / 'games' / 'duel').is_dir())

    def test_it_is_text_that_says_which_version_it_is(self):
        raw = json.loads((self.where / 'replay.json').read_text())
        self.assertEqual(1, raw['version'])
        self.assertEqual('duel', raw['game'])

    def test_it_spans_the_setup_state_and_the_round_that_was_played(self):
        self.assertEqual((10, 20), (self.exported['first_tick'], self.exported['last_tick']))

    def test_everything_that_was_ever_in_space_is_in_it(self):
        alpha = self.named('Alpha')
        self.assertEqual(list(range(10, 21)), [t['tick'] for t in alpha['ticks']])
        self.assertEqual('Alpha', alpha['owner'])          # a ship's owner is itself
        rocket = self.named('Alpha-Rocket-R1-1')
        self.assertEqual([11, 12], [t['tick'] for t in rocket['ticks']])
        self.assertEqual('One', rocket['faction'])         # reached through whoever fired it
        # The ship that died is in it, and stops at the tick it died on.
        self.assertLess(self.named('Beta')['ticks'][-1]['tick'], self.exported['last_tick'])

    def test_it_keeps_who_flew_it(self):
        self.assertEqual('Menno', self.named('Alpha')['player'])
        self.assertIsNone(self.named('Alpha-Rocket-R1-1')['player'])

    def test_it_keeps_the_condition_the_replay_screen_does_not_show(self):
        ticks = self.named('Beta')['ticks']
        self.assertLess(ticks[-1]['hull'], ticks[0]['hull'])
        self.assertIsNotNone(ticks[0]['battery'])
        self.assertTrue(any('Shields' in t['components'] for t in ticks))

    def test_it_keeps_what_the_kill_was_worth(self):
        self.assertGreater(sum(t['score'] for t in self.named('Alpha')['ticks']), 0)

    def test_it_keeps_what_each_ship_saw(self):
        """Without the scans there is no fog left to watch a finished game through."""
        seen = {s['name'] for t in self.named('Alpha')['ticks'] for s in t['scans']}
        self.assertIn('Beta', seen)
        at_ten = next(t for t in self.named('Alpha')['ticks'] if t['tick'] == 10)
        beta = next(s for s in at_ten['scans'] if s['name'] == 'Beta')
        self.assertEqual((0, 20), (beta['x'], beta['y']))   # where it was, and nothing else

    def test_something_that_never_looks_saw_nothing(self):
        self.assertEqual([], self.named('Alpha-Rocket-R1-1')['ticks'][0]['scans'])

    def test_an_event_says_where_it_happened(self):
        fired = next(e for t in self.named('Alpha')['ticks'] for e in t['events']
                     if 'fired' in e['text'])
        self.assertTrue(fired['kind'])
        self.assertEqual({}, fired['shape'])       # it happened where it says it did

    def test_a_beam_manifests_as_the_line_it_ran_along(self):
        tick = next(t for t in self.named('Alpha')['ticks'] if t['tick'] == 11)
        beam = next(e for e in tick['events'] if 'line' in e['shape'])
        self.assertEqual({'x1': 0, 'y1': -20, 'x2': 0, 'y2': 20}, beam['shape']['line'])
        self.assertEqual((0, 20), (beam['x'], beam['y']))    # anchored where it landed
        self.assertEqual('Laser', beam['damage_type'])       # and what it was struck with

    def test_a_blast_manifests_as_the_circle_it_covered(self):
        blast = next(e for o in self.exported['objects'] for t in o['ticks'] for e in t['events']
                     if 'circle' in e['shape'])
        self.assertEqual('explosion', blast['kind'])
        self.assertGreater(blast['shape']['circle']['radius'], 0)
        self.assertEqual((blast['x'], blast['y']),
                         (blast['shape']['circle']['x'], blast['shape']['circle']['y']))

    def test_exporting_again_overwrites(self):
        again = Path(self.admin.export_to_valhalla('duel'))
        self.assertEqual(self.where, again)
        self.assertEqual(len(self.exported['objects']),
                         len(valhalla.load((again / 'replay.json').read_text())['objects']))

    def test_a_version_this_code_cannot_read_is_refused_by_number(self):
        with self.assertRaises(ValueError) as refused:
            valhalla.load(json.dumps({'version': 99}))
        self.assertIn('99', str(refused.exception))

    def test_a_document_that_is_not_what_v1_promises_is_refused(self):
        self.exported['objects'][0]['nickname'] = 'Bertha'
        with self.assertRaises(ValidationError):
            valhalla.load(json.dumps(self.exported))
        del self.exported['objects'][0]['nickname']
        del self.exported['objects'][0]['radius']
        with self.assertRaises(ValidationError):
            valhalla.load(json.dumps(self.exported))


class TestAFileWrittenEarlierStillReads(TestCase):
    """A v1 file that no current code produced. Change what v1 means and this stops working."""

    def setUp(self):
        self.doc = valhalla.load(EXAMPLE.read_text())

    def named(self, name):
        return next(o for o in self.doc['objects'] if o['name'] == name)

    def test_it_reads_as_the_version_it_says(self):
        self.assertEqual(1, self.doc['version'])
        self.assertEqual('Skirmish', self.doc['game'])
        self.assertEqual((10, 11), (self.doc['first_tick'], self.doc['last_tick']))

    def test_the_fields_still_mean_what_they_meant(self):
        alpha = self.named('Alpha')
        self.assertEqual('Menno', alpha['player'])
        self.assertEqual(167, alpha['ticks'][1]['score'])
        self.assertEqual('20/100', alpha['ticks'][1]['components']['L1']['Temperature'])
        self.assertEqual('hit', alpha['ticks'][1]['events'][0]['kind'])

    def test_something_that_was_never_built_answers_nothing(self):
        rock = self.named('Rock')
        self.assertEqual([None, None], [t['hull'] for t in rock['ticks']])
        self.assertEqual([{}, {}], [t['components'] for t in rock['ticks']])
        self.assertEqual(15, rock['radius'])

    def test_the_shapes_still_manifest(self):
        struck, blast = self.named('Alpha')['ticks'][1]['events']
        self.assertEqual({'x1': 0, 'y1': -20, 'x2': 0, 'y2': 20}, struck['shape']['line'])
        self.assertEqual({'x': 0, 'y': 20, 'radius': 30}, blast['shape']['circle'])
        self.assertEqual(['Laser', 'Explosion'], [struck['damage_type'], blast['damage_type']])

    def test_what_was_seen_still_reads(self):
        self.assertEqual([{'name': 'Beta', 'x': 0, 'y': 20}, {'name': 'Rock', 'x': 60, 'y': 0}],
                         self.named('Alpha')['ticks'][0]['scans'])
