import unittest

from engine.round import GameRound
from engine.admin import setup_game
from engine.gamedirectory import GameDirectory
from log import deactivate_logger_blocklist


class TestGames(unittest.TestCase):
    def setUp(self):
        deactivate_logger_blocklist()

    @staticmethod
    def _setup_game(game_name: str) -> GameDirectory:
        gd = GameDirectory('./test/test-games', game_name)
        setup_game(gd)
        return gd

    @staticmethod
    def _run(gd: GameDirectory, nr_of_rounds: int):
        for i in range(1, nr_of_rounds + 1):
            GameRound(gd, i).do_round()

    def test_game_1(self):
        gd = self._setup_game('test-game')
        ships_0 = gd.load_current_status()
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
        self._run(gd, number_of_rounds)

        self.assertEqual(gd.last_round_number, number_of_rounds)
        ships_1 = gd.load_current_status()
        self.assertEqual(ships_1['Blaster-1'].score, total_score)


