"""A round this code cannot read says which game it is, and never takes a list down with it.

`test-games/unreadable` is a real world saved before `DrawType` was removed from the engine, kept
because no amount of regenerating can produce one again.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from arena.app.services import AdminService, GameService
from arena.cfg import REPO_ROOT
from arena.errors import UnreadableWorld

BROKEN = 'unreadable'
FIXTURE = Path(REPO_ROOT) / 'test' / 'test-games' / BROKEN

PLAYING = [{'name': 'Alpha', 'type': 'H2545', 'faction': 'One', 'player': 'Menno', 'x': 0, 'y': 0}]


class TestAnUnreadableGame(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        shutil.copytree(FIXTURE, self.root / 'games' / BROKEN)
        self.admin = AdminService(str(self.root))
        self.game = GameService(str(self.root))
        self.admin.issue_login('Menno')
        self.admin.create_game('healthy', PLAYING, 'generic')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_asking_it_for_its_standing_says_which_game(self):
        with self.assertRaises(UnreadableWorld) as caught:
            self.admin.standing(BROKEN)

        self.assertEqual(BROKEN, caught.exception.game)

    def test_a_list_holding_it_still_answers_for_the_others(self):
        listed = {g.name: g.standing for g in self.admin.list_games()}

        self.assertIsNone(listed[BROKEN])
        self.assertIsNotNone(listed['healthy'])

    def test_it_keeps_nobody_from_logging_in(self):
        self.assertEqual(['healthy'], self.game.games_for_player('Menno'))

    def test_it_is_listed_rather_than_hidden(self):
        """The list is where a director goes to fix it, so it has to be in one."""
        self.assertIn(BROKEN, {g.name for g in self.admin.list_games()})

    def test_the_round_it_is_on_is_read_without_loading_it(self):
        """What a regenerate starts from, and the reason that is not a summary."""
        self.assertEqual(0, self.admin.playable_games_on_disk()[BROKEN])

    def test_it_reports_what_the_code_no_longer_has(self):
        stale = self.admin.stale_rounds(BROKEN)

        self.assertEqual([0], [r.round_nr for r in stale])
        self.assertEqual({'arena.engine.objects.event.DrawType': 1}, stale[0].missing)
        self.assertEqual('', stale[0].error)
        self.assertFalse(stale[0].reads)

    def test_a_game_it_can_read_reports_nothing_missing(self):
        self.assertTrue(all(r.reads for r in self.admin.stale_rounds('healthy')))