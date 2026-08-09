import os
import shutil
import tempfile
from unittest import TestCase

from arena.app.services import AdminService, GameService

SHIPS = [{'name': 'Alpha', 'type': 'A2527', 'faction': 'One', 'player': 'Serge', 'x': 0, 'y': 0}]


class TestArchiving(TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.games = os.path.join(self.root, 'games')
        self.admin = AdminService(self.root)
        self.game = GameService(self.root)
        for name in ('live', 'old'):
            self.admin.create_game(name, SHIPS, 'generic')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def names(self, summaries):
        return [s.name for s in summaries]

    def test_archiving_moves_it_out_of_every_list(self):
        self.admin.archive_game('old')
        self.assertEqual(['live'], self.names(self.admin.list_games()))
        self.assertEqual(['old'], self.names(self.admin.list_archived_games()))
        # The player's games and the claimable-name check both go through list_games.
        self.assertEqual(['live'], self.game.games_for_player('Serge'))

    def test_the_archive_sits_beside_the_games(self):
        self.admin.archive_game('old')
        self.assertTrue(os.path.isdir(os.path.join(self.root, 'archived', 'old')))
        self.assertFalse(os.path.exists(os.path.join(self.games, 'old')))

    def test_nothing_is_lost_in_archiving(self):
        self.admin.archive_game('old')
        with open(os.path.join(self.root, 'archived', 'old', 'ships.jsonl')) as f:
            self.assertIn('Alpha', f.read())

    def test_unarchiving_puts_it_back(self):
        self.admin.archive_game('old')
        self.admin.unarchive_game('old')
        self.assertEqual(['live', 'old'], self.names(self.admin.list_games()))
        self.assertEqual([], self.names(self.admin.list_archived_games()))

    def test_archiving_twice_is_refused(self):
        self.admin.archive_game('old')
        os.makedirs(os.path.join(self.games, 'old'))
        with self.assertRaises(ValueError):
            self.admin.archive_game('old')

    def test_unarchiving_onto_a_live_name_is_refused(self):
        self.admin.archive_game('old')
        os.makedirs(os.path.join(self.games, 'old'))
        with self.assertRaises(ValueError):
            self.admin.unarchive_game('old')

    def test_delete_only_reaches_into_the_archive(self):
        self.admin.archive_game('old')
        self.admin.delete_archived_game('old')
        self.assertEqual([], self.names(self.admin.list_archived_games()))
        self.assertEqual(['live'], self.names(self.admin.list_games()))
        # A live game of the same name would have to be archived first.
        with self.assertRaises(FileNotFoundError):
            self.admin.delete_archived_game('live')
        self.assertTrue(os.path.isdir(os.path.join(self.games, 'live')))

    def test_a_game_may_be_called_archived(self):
        os.makedirs(os.path.join(self.games, 'archived'))
        self.assertIn('archived', self.names(self.admin.list_games()))