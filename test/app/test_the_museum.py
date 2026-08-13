"""A finished game, watched. The picture comes off a file rather than off the saved worlds.

The point of the first class is that the two builders agree. `game_replay` walks a played game's
worlds and `from_valhalla` walks its export, and the map above them is handed one shape either
way, so the moment they drift this fails.
"""
import json
import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path
from unittest import TestCase

from arena.app import from_valhalla
from arena.app.services import AdminService, GameService

# Twenty apart and pointed at each other, so every rocket goes off in the round it was fired.
DUEL = [{'name': 'Alpha', 'type': 'H2545', 'faction': 'One', 'player': 'Menno', 'x': 0, 'y': -20},
        {'name': 'Beta', 'type': 'A2527', 'faction': 'Two', 'player': 'Rik', 'x': 0, 'y': 20}]

EXAMPLE = Path(__file__).parent / 'valhalla-v1-example.json'


class TestTheTwoBuildersAgree(TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.admin = AdminService(str(self.root))
        self.game = GameService(str(self.root))
        self.admin.create_game('duel', DUEL, 'generic')
        self.game.save_commands('duel', 'Alpha',
                                [f'{t}: Fire R1 0' for t in range(1, 6)] + ['1: Fire L1 Beta'])
        self.game.save_commands('duel', 'Beta', ['1: Scan'])
        self.admin.process_turn('duel')
        self.admin.export_to_valhalla('duel')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def both(self, faction=None):
        return (self.game.game_replay('duel', faction), self.game.valhalla_replay('duel', faction))

    def test_every_side_at_once_is_the_same_game(self):
        played, museum = self.both()
        self.assertEqual(asdict(played), asdict(museum))

    def test_one_side_sees_the_same_war(self):
        for faction in ('One', 'Two'):
            with self.subTest(faction=faction):
                played, museum = self.both(faction)
                self.assertEqual(asdict(played), asdict(museum))

    def test_a_side_that_never_flew_is_refused_rather_than_answered_empty(self):
        with self.assertRaises(ValueError):
            self.game.valhalla_replay('duel', 'Three')

    def test_the_museum_lists_what_is_in_it(self):
        listed = self.game.list_finished_games()
        self.assertEqual(['duel'], [g.name for g in listed])
        self.assertEqual(1, listed[0].rounds)
        self.assertEqual(['One', 'Two'], listed[0].factions)
        self.assertEqual(['Menno', 'Rik'], listed[0].players)

    def test_a_finished_game_keeps_its_name(self):
        self.admin.archive_game('duel')
        self.assertIn('duel', self.admin.game_names_in_use())


class TestAFileWrittenEarlierStillPlays(TestCase):
    """A v1 file no current code produced, watched the way the museum watches one."""

    def setUp(self):
        self.doc = json.loads(EXAMPLE.read_text())

    def shown(self, replay, name):
        return next(o for o in replay.objects if o.name == name)

    def test_every_side_at_once_holds_everything_that_was_there(self):
        replay = from_valhalla.replay(self.doc)
        self.assertEqual({'Alpha', 'Beta', 'Rock'}, {o.name for o in replay.objects})
        self.assertEqual((10, 11), (replay.first_tick, replay.last_tick))
        self.assertFalse(any(o.contact for o in replay.objects))

    def test_a_side_holds_its_own_whole_and_everything_else_as_sightings(self):
        replay = from_valhalla.replay(self.doc, 'One')
        self.assertFalse(self.shown(replay, 'Alpha').contact)
        self.assertEqual([10], [p.abs_tick for p in self.shown(replay, 'Beta').path])
        self.assertTrue(self.shown(replay, 'Beta').contact)
        # Seen at both ticks, by the one commander that looked.
        self.assertEqual([10, 11], [p.abs_tick for p in self.shown(replay, 'Rock').path])

    def test_a_sighting_says_where_and_never_which_way(self):
        seen = self.shown(from_valhalla.replay(self.doc, 'One'), 'Beta').path[0]
        self.assertEqual((0, 20), (seen.x, seen.y))
        self.assertEqual((None, None), (seen.heading, seen.speed))

    def test_what_a_side_never_looked_at_is_not_in_its_picture(self):
        """Beta scanned Alpha and never the rock, so the rock is not in Two's war at all."""
        replay = from_valhalla.replay(self.doc, 'Two')
        self.assertEqual({'Beta', 'Alpha'}, {o.name for o in replay.objects})
        self.assertTrue(self.shown(replay, 'Alpha').contact)

    def test_a_beam_is_the_line_it_ran_along_whoever_is_watching(self):
        for faction in (None, 'One'):
            with self.subTest(faction=faction):
                beam = from_valhalla.replay(self.doc, faction).beams[0]
                self.assertEqual((0, -20, 0, 20), (beam.x1, beam.y1, beam.x2, beam.y2))
                self.assertEqual((1, 11), (beam.tick, beam.abs_tick))
                self.assertEqual('Laser', beam.damage_type)

    def test_a_version_nothing_here_builds_is_refused(self):
        with self.assertRaises(KeyError):
            from_valhalla.replay(dict(self.doc, version=99))