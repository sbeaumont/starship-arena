import os.path
import unittest

from arena.engine.game import Game
from arena.engine.admin import setup_game
from arena.engine.gamedirectory import GameDirectory
from arena.log import deactivate_logger_blocklist


class TestGames(unittest.TestCase):
    def setUp(self):
        deactivate_logger_blocklist()

    def _setup_game(self, game_name: str) -> Game:
        self.test_dir = './test/test-games'
        gd = GameDirectory(self.test_dir, game_name)
        return setup_game(gd)

    def _run(self, game: Game, nr_of_rounds: int):
        for i in range(1, nr_of_rounds + 1):
            game.init_round(i)
            self.assertTrue(game.round_ready)
            game.do_round()

    def test_game_1(self):
        game = self._setup_game('test-game')
        ships_0 = game._dir.load_current_status()
        ship = ships_0['Shaper-1']
        total_score = 0
        shield = ship.defense[0]
        # Half point per hit on shield
        total_score += shield.strengths['W'] // 2
        # Shield break bonus
        total_score += shield.shield_break_score
        # Point per hit on hull
        total_score += ship.hull
        # Ship kill bonus
        total_score += 100

        number_of_rounds = 1
        self._run(game, number_of_rounds)

        self.assertEqual(game._dir.last_round_number, number_of_rounds)
        ships_1 = game._dir.load_current_status()
        self.assertEqual(ships_1['Blaster-1'].score, total_score)
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, 'test-game', 'round-0')))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, 'test-game', 'round-1')))


