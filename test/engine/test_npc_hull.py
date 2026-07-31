"""A ship with no player is nobody's, so nobody is asked to write it orders."""
import os
import shutil
import tempfile
from unittest import TestCase

from arena.engine.admin import GameSetup
from arena.engine.game import Game
from arena.engine.gamedirectory import GameDirectory, ShipFile

ROSTER = [
    {'name': 'Voyager', 'type': 'H2545', 'faction': 'One', 'player': 'Rik', 'x': 0, 'y': 0},
    {'name': 'Derelict', 'type': 'H2552', 'faction': 'Two', 'x': 200, 'y': 0},
]


class TestAHullWithNoPlayer(TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.gd = GameDirectory(self.root, 'npc')
        self.gd.setup_directories()
        GameSetup(self.gd, ShipFile(self.gd, ROSTER)).execute()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _orders(self, ship: str, text: str):
        with open(os.path.join(self.root, 'npc', 'commands', f'{ship}-commands-1.txt'), 'w') as f:
            f.write(text)

    def test_it_is_not_counted_as_a_player_ship(self):
        game = Game(self.gd)
        self.assertEqual(['Voyager'], [s.name for s in game.player_ships])
        self.assertEqual({'Rik'}, game.players)

    def test_no_orders_are_expected_for_it(self):
        self.assertEqual(['Voyager'], sorted(Game(self.gd).missing_command_files))

    def test_the_round_runs_once_the_players_have_written_theirs(self):
        self._orders('Voyager', "1: A10\n")

        game = Game(self.gd)
        self.assertTrue(game.current_round_ready)
        game.process_current_round()

        self.assertEqual(1, self.gd.last_round_number)
        self.assertIn('Derelict', self.gd.load_current_status())

    def test_the_roster_written_back_still_has_no_player_for_it(self):
        roster = {line.name: line for line in ShipFile(self.gd).ship_lines}
        self.assertEqual('Rik', roster['Voyager'].player)
        self.assertEqual('', roster['Derelict'].player)