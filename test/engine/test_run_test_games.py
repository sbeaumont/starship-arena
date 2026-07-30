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
            self.assertTrue(game.current_round_ready)
            game.process_current_round()

    def test_game_1(self):
        """Blaster-1 shoots Shaper-1's west shield down and kills it, and is paid for both.

        Not an exact total: damage arrives in as many chunks as there are hits, and the shield
        pays half a point per damage rounded down, so the sum depends on the shot timing.
        """
        game = self._setup_game('test-game')
        target = game._dir.load_current_status()['Shaper-1']
        shield = target.defense[0]
        self.assertGreater(shield.strengths['W'], 0)
        without_shield_damage = shield.shield_break_score + target.hull + target.kill_score

        number_of_rounds = 1
        self._run(game, number_of_rounds)

        self.assertEqual(number_of_rounds, game._dir.last_round_number)
        ships_1 = game._dir.load_current_status()
        wreck = game._dir.load_graveyard()['Shaper-1']

        self.assertNotIn('Shaper-1', ships_1)
        self.assertEqual(0, wreck.defense[0].strengths['W'])
        self.assertGreater(ships_1['Blaster-1'].score, without_shield_damage)


