import os
import shutil
import tempfile
from unittest import TestCase

from arena.app.services import AdminService, GameService

SHIPS = [{'name': 'Alpha', 'type': 'A2527', 'faction': 'One', 'player': 'Serge', 'x': 0, 'y': 0}]


class TestFinishing(TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.admin = AdminService(self.root)
        self.game = GameService(self.root)
        for name in ('live', 'over'):
            self.admin.create_game(name, SHIPS, 'generic')
        self.admin.finish_game('over')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def names(self, summaries):
        return [s.name for s in summaries]

    def test_it_sits_in_its_own_root(self):
        self.assertTrue(os.path.isdir(os.path.join(self.root, 'finished', 'over')))
        self.assertEqual(['live'], self.names(self.admin.list_games()))
        self.assertEqual(['over'], self.names(self.admin.list_finished_games()))

    def test_the_players_still_see_it(self):
        self.assertEqual(['live', 'over'], sorted(self.game.games_for_player('Serge')))

    def test_it_still_reads(self):
        self.assertEqual(['Alpha'], self.game.list_ships('over'))

    def test_no_orders_are_taken(self):
        with self.assertRaises(ValueError):
            self.game.save_commands('over', 'Alpha', ['1: L30'])
        with self.assertRaises(ValueError):
            self.game.set_ready('over', 'Serge', True)

    def test_no_round_is_processed(self):
        with self.assertRaises(ValueError):
            self.admin.process_turn('over')

    def test_the_name_is_still_claimed(self):
        self.assertIn('over', self.admin.game_names_in_use())
        with self.assertRaises(ValueError):
            self.admin.create_game('over', SHIPS, 'generic')

    def test_it_goes_back_into_play(self):
        self.admin.activate_game('over')
        self.assertEqual(['live', 'over'], self.names(self.admin.list_games()))
        self.game.save_commands('over', 'Alpha', ['1: L30'])

    def test_it_can_be_archived_from_here(self):
        self.admin.archive_game('over')
        self.assertEqual(['over'], self.names(self.admin.list_archived_games()))
        self.assertEqual([], self.names(self.admin.list_finished_games()))
        self.assertEqual(['live'], self.game.games_for_player('Serge'))