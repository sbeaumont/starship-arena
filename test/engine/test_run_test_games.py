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
        """Blaster-1 shoots Shaper-1's stern shield down and kills it, and is paid for both.

        Blaster sits due south and both face north, so every rocket lands on S. Quadrants are
        relative to the target, which is the whole point of being able to turn a good face to
        something.

        Not an exact total: damage arrives in as many chunks as there are hits, and the shield
        pays half a point per damage rounded down, so the sum depends on the shot timing.
        """
        game = self._setup_game('test-game')
        target = game._dir.load_current_world().objects['Shaper-1']
        shield = target.defense[0]
        self.assertGreater(shield.strengths['S'], 0)
        without_shield_damage = shield.shield_break_score + target.hull + target.kill_score

        number_of_rounds = 1
        self._run(game, number_of_rounds)

        self.assertEqual(number_of_rounds, game._dir.last_round_number)
        final = game._dir.load_current_world()
        ships_1 = final.objects
        wreck = final.graveyard['Shaper-1']

        self.assertNotIn('Shaper-1', ships_1)
        self.assertEqual(0, wreck.defense[0].strengths['S'])
        self.assertGreater(ships_1['Blaster-1'].score, without_shield_damage)


