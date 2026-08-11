"""A game's replay holds every object that was ever in space, tick by tick."""
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase

from arena.app.services import AdminService, GameService

# Twenty apart and pointed at each other, so every rocket goes off in the round it was fired.
DUEL = [{'name': 'Alpha', 'type': 'H2545', 'faction': 'One', 'player': 'Menno', 'x': 0, 'y': -20},
        {'name': 'Beta', 'type': 'A2527', 'faction': 'Two', 'player': 'Rik', 'x': 0, 'y': 20}]


class TestReplayingAGame(TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.admin = AdminService(str(self.root))
        self.game = GameService(str(self.root))
        for who in ('Menno', 'Rik'):
            self.admin.issue_login(who)
        self.admin.create_game('duel', DUEL, 'generic')
        self.game.save_commands('duel', 'Alpha', [f'{t}: Fire R1 0' for t in range(1, 6)])
        self.game.save_commands('duel', 'Beta', [])
        self.admin.process_turn('duel')
        self.replay = self.game.game_replay('duel')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def named(self, name):
        return next(o for o in self.replay.objects if o.name == name)

    def test_it_spans_the_setup_state_and_the_round_that_was_played(self):
        self.assertEqual(10, self.replay.first_tick)
        self.assertEqual(20, self.replay.last_tick)
        self.assertIsNone(self.replay.faction)   # every side, which is the director's view

    def test_a_ship_has_a_row_for_every_tick_in_order(self):
        alpha = self.named('Alpha')
        self.assertEqual(list(range(10, 21)), [t.abs_tick for t in alpha.path])
        self.assertEqual('Alpha', alpha.owner)   # a ship's owner is itself

    def test_ordnance_is_there_for_the_ticks_it_flew_and_says_whose_it_is(self):
        rocket = self.named('Alpha-Rocket-R1-1')
        self.assertEqual([11, 12], [t.abs_tick for t in rocket.path])
        self.assertEqual('Alpha', rocket.owner)
        # It carries no faction of its own, so the side it reports is the one it is reached
        # through: whoever fired it.
        self.assertEqual('One', rocket.faction)
        self.assertFalse(rocket.contact)

    def test_a_destroyed_ship_stops_before_the_last_tick(self):
        self.assertLess(self.named('Beta').path[-1].abs_tick, self.replay.last_tick)

    def test_every_row_carries_where_and_which_way(self):
        for o in self.replay.objects:
            for row in o.path:
                self.assertIsNotNone(row.x, o.name)
                self.assertIsNotNone(row.heading, o.name)

    def test_events_are_stamped_with_both_numbers_for_the_moment(self):
        fired = next(e for e in self.named('Alpha').events if 'fired' in e.text)
        self.assertEqual(1, fired.tick)
        self.assertEqual(11, fired.abs_tick)


class TestWatchingOneSide(TestReplayingAGame):
    """One faction's war: its own objects as they were, and everything else as its ships saw it."""

    def setUp(self):
        super().setUp()
        self.replay = self.game.game_replay('duel', 'One')

    def own(self):
        return [o for o in self.replay.objects if not o.contact]

    def seen(self):
        return [o for o in self.replay.objects if o.contact]

    def test_nothing_of_another_side_is_built_as_itself(self):
        self.assertEqual('One', self.replay.faction)
        self.assertEqual({'One'}, {o.faction for o in self.own()})
        self.assertIn('Alpha-Rocket-R1-1', [o.name for o in self.own()])

    def test_the_enemy_is_there_only_where_it_was_seen(self):
        beta = next(o for o in self.seen() if o.name == 'Beta')
        self.assertEqual('Two', beta.faction)
        self.assertTrue(all(r.heading is None for r in beta.path))
        self.assertEqual([], beta.events)

    def test_a_sighting_is_one_point_a_tick_however_many_ships_looked(self):
        for o in self.seen():
            ticks = [r.abs_tick for r in o.path]
            self.assertEqual(sorted(set(ticks)), ticks, o.name)

    # The base class asserts the director's view of these two.
    def test_it_spans_the_setup_state_and_the_round_that_was_played(self):
        self.assertEqual((10, 20), (self.replay.first_tick, self.replay.last_tick))
        self.assertEqual('One', self.replay.faction)

    def test_a_destroyed_ship_stops_before_the_last_tick(self):
        self.assertLess(self.named('Beta').path[-1].abs_tick, self.replay.last_tick)

    def test_every_row_carries_where_and_which_way(self):
        for o in self.own():
            for row in o.path:
                self.assertIsNotNone(row.heading, o.name)