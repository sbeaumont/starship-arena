"""What a faction's blows did reaches the player's plan, placed and facing the right way."""
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase

from arena.app.services import AdminService, GameService

# Twenty apart and pointed at each other, which is inside a laser's reach of 60.
DUEL = [{'name': 'Alpha', 'type': 'H2545', 'faction': 'One', 'player': 'Menno', 'x': 0, 'y': -20},
        {'name': 'Beta', 'type': 'A2527', 'faction': 'Two', 'player': 'Rik', 'x': 0, 'y': 20}]


class TestBlowsReachTheMap(TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.admin = AdminService(str(self.root))
        self.game = GameService(str(self.root))
        for who in ('Menno', 'Rik'):
            self.admin.issue_login(who)
        self.admin.create_game('duel', DUEL, 'generic')
        self.game.save_commands('duel', 'Alpha', [f'{t}: Fire L1 Beta' for t in range(1, 11)])
        self.game.save_commands('duel', 'Beta', [])
        self.admin.process_turn('duel')
        self.effects = self.game.get_player_plan('duel', 'Menno').effects

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def outcomes(self, part):
        return [e.outcome for e in self.effects if e.part == part]

    def test_the_shield_holds_and_then_gives_way(self):
        self.assertEqual('Damaged', self.outcomes('Shields')[0])
        self.assertIn('Breached', self.outcomes('Shields'))

    def test_the_hull_is_reached_after_that(self):
        breach = next(e for e in self.effects if e.outcome == 'Breached')
        first_hull = next(e for e in self.effects if e.part == 'hull')
        self.assertLessEqual(breach.tick, first_hull.tick)

    def test_each_one_is_placed_where_the_target_was(self):
        self.assertEqual({(0.0, 20.0)}, {(e.x, e.y) for e in self.effects})

    def test_each_one_faces_whoever_landed_it(self):
        """Alpha is due south of Beta, so every blow arrives on Beta's southern face."""
        self.assertEqual({180.0}, {e.bearing for e in self.effects})

    def test_only_your_own_faction_s_blows_are_in_it(self):
        self.assertEqual({'Beta'}, {e.target for e in self.effects})

    def test_the_log_line_says_the_whole_thing_in_one_go(self):
        plan = self.game.get_player_plan('duel', 'Menno')
        hits = [e for e in plan.ships[0].events if e.kind == 'hit']
        self.assertTrue(hits)
        self.assertIn('Shields Damaged', hits[0].text)

    def test_the_one_who_was_hit_sees_it_too(self):
        """The blow is one message, and the world already has it."""
        theirs = self.game.get_player_plan('duel', 'Rik')
        self.assertTrue([e for e in theirs.ships[0].events if e.kind == 'hit'])
        # Their own plan holds no effects: they landed none.
        self.assertEqual([], theirs.effects)