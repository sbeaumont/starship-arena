"""A replay answers any tick of a played game from the world saved for that tick's round."""
import os
import shutil
import tempfile
from unittest import TestCase

from arena.app.services import AdminService, GameService
from arena.engine.gamedirectory import GameDirectory
from arena.engine.history import TICK_ZERO, Tick
from arena.engine.replay import Replay

# Far enough apart that a rocket fired on tick 2 is still in flight when the round ends.
APART = [{'name': 'Alpha', 'type': 'H2545', 'faction': 'One', 'player': 'Menno', 'x': 0, 'y': -300},
         {'name': 'Beta', 'type': 'A2527', 'faction': 'Two', 'player': 'Rik', 'x': 0, 'y': 300}]

# Twenty apart and pointed at each other, which is well inside a laser's reach.
POINT_BLANK = [dict(APART[0], y=-20), dict(APART[1], y=20)]


class _Duel(TestCase):
    roster = APART
    orders = ['2: Fire R1 0']

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.admin, self.game = AdminService(self.root), GameService(self.root)
        for who in ('Menno', 'Rik'):
            self.admin.issue_login(who)
        self.admin.create_game('duel', self.roster, 'generic')
        self.game.save_commands('duel', 'Alpha', self.orders)
        self.game.save_commands('duel', 'Beta', [])
        self.admin.process_turn('duel')
        self.replay = Replay(GameDirectory(os.path.join(self.root, 'games'), 'duel'))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def ticks_holding(self, name: str) -> list[int]:
        return [t.abs_tick for t in self.replay.ticks if name in self.replay.objects_at(t)]


class TestScrubbingARound(_Duel):
    def test_it_runs_from_the_setup_state_to_the_last_tick_played(self):
        self.assertEqual(TICK_ZERO, self.replay.first)
        self.assertEqual(Tick(1, 10), self.replay.last)
        self.assertEqual(11, len(self.replay.ticks))

    def test_a_tick_is_answered_by_the_world_saved_for_its_round(self):
        self.assertIs(self.replay.worlds[0], self.replay.world_at(TICK_ZERO))
        self.assertIs(self.replay.worlds[1], self.replay.world_at(Tick(1, 4)))

    def test_only_the_roster_is_in_space_before_the_first_round(self):
        self.assertEqual(['Alpha', 'Beta'], sorted(self.replay.objects_at(TICK_ZERO)))

    def test_ordnance_is_there_from_the_tick_it_was_launched(self):
        self.assertEqual(['Alpha', 'Beta'], sorted(self.replay.objects_at(Tick(1, 1))))
        self.assertIn('Alpha-Rocket-R1-1', self.replay.objects_at(Tick(1, 2)))
        self.assertEqual(list(range(12, 21)), self.ticks_holding('Alpha-Rocket-R1-1'))

    def test_everything_it_hands_back_has_a_snapshot_for_the_tick(self):
        for tick in self.replay.ticks:
            for name, ois in self.replay.objects_at(tick).items():
                self.assertIn('pos', ois.history[tick], f"{name} has nothing at {tick}")


class TestWhatDiedInTheRound(_Duel):
    """Point blank, so every rocket goes off in the round it was fired and the ship gives way."""
    roster = POINT_BLANK
    orders = [f'{t}: Fire R1 0' for t in range(1, 6)]   # a laser alone does not finish an A2527

    def test_the_dead_ship_is_in_the_graveyard_and_in_the_round_that_killed_it(self):
        self.assertIn('Beta', self.replay.worlds[1].graveyard)
        self.assertIn('Beta', self.replay.worlds[1].destroyed)

    def test_a_ship_answers_up_to_the_tick_it_died_on_and_no_further(self):
        seen = self.ticks_holding('Beta')
        self.assertEqual(list(range(seen[0], seen[-1] + 1)), seen)
        self.assertLess(seen[-1], self.replay.last.abs_tick)
        self.assertEqual(self.replay.last.abs_tick, self.ticks_holding('Alpha')[-1])

    def test_ordnance_that_went_off_still_flies_the_ticks_it_flew(self):
        rocket = 'Alpha-Rocket-R1-1'
        self.assertNotIn(rocket, self.replay.worlds[1].objects)
        self.assertNotIn(rocket, self.replay.worlds[1].graveyard)
        self.assertEqual([11, 12], self.ticks_holding(rocket))   # fired on 1, went off on 2

    def test_the_round_that_killed_them_holds_every_one(self):
        self.assertEqual(sorted(self.replay.worlds[1].destroyed),
                         sorted({name for tick in self.replay.ticks
                                 for name in self.replay.objects_at(tick)}
                                - set(self.replay.worlds[1].objects)))