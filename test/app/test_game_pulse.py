import os
import shutil
import tempfile
from unittest import TestCase

from arena.app.services import AdminService, GameService

SHIPS = """Name  Type   Faction Player X Y
Alpha A2527  One     Serge  0 0
Bravo A2527  Two     Ilya   100 100
"""


class TestGamePulse(TestCase):
    """The console's poll, which has to answer without loading a round."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        games = os.path.join(self.root, 'games')
        os.makedirs(games)
        self.admin = AdminService(games)
        self.game = GameService(games)
        self.admin.create_game('live', SHIPS)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_a_fresh_game_owes_everything(self):
        pulse = self.admin.game_pulse('live')
        self.assertEqual(1, pulse.round_nr)
        self.assertEqual({'Alpha': False, 'Bravo': False}, pulse.orders)
        self.assertEqual({'Ilya': False, 'Serge': False}, pulse.ready)

    def test_it_sees_orders_arrive(self):
        self.game.save_commands('live', 'Alpha', ['turn 10'])
        self.assertEqual({'Alpha': True, 'Bravo': False}, self.admin.game_pulse('live').orders)

    def test_it_sees_a_player_say_ready(self):
        self.admin.set_ready('live', 'Serge', True)
        self.assertEqual({'Ilya': False, 'Serge': True}, self.admin.game_pulse('live').ready)