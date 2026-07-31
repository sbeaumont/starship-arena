import unittest

from arena.engine.admin import setup_game
from arena.engine.game import Game
from arena.engine.gamedirectory import ShipFile
from arena.log import deactivate_logger_blocklist

ship_1_name = "Poodle"
ship_2_name = "PoodleII"


original_ship_file = [
    {'name': ship_1_name, 'type': 'H2545', 'faction': 'One', 'player': 'Serge', 'x': 1, 'y': 0},
    {'name': ship_2_name, 'type': 'H2552', 'faction': 'Two', 'player': 'Piet', 'x': 122, 'y': 0},
]

# A weapon takes one order per tick, so the two rockets a tick come from the two launchers.
command_ship_1_1 = """
    1: Fire S1 45
    1: Fire R1 90
    1: Fire R2 90
    2: Fire S1 90
    2: Fire R1 90
    2: Fire R2 90
    3: Fire S1 90
    3: Fire R1 90
    3: Fire R2 90
"""

commands = {
    (ship_1_name, 1): command_ship_1_1,
    (ship_2_name, 1): ''
}


class MockGameDirectory(object):
    def __init__(self):
        self.path = ''
        self.world = None
        self.round_number = 0

    def setup_directories(self):
        pass

    def clean(self):
        pass

    @property
    def init_file(self) -> str:
        return 'mock_init_file_name'

    @property
    def game_name(self) -> str:
        return 'mock_game_name'

    def save_world(self, world, nr):
        self.world = world
        self.round_number = nr

    def load_current_world(self):
        return self.world

    def load_world(self, round_nr: int):
        return self.world

    def command_file_exists(self, ship_name, round_nr):
        return (ship_name, round_nr) in commands

    def read_command_file(self, ship_name, round_nr):
        return commands[(ship_name, round_nr)].splitlines()

    def status_file_for_round_exists(self, round_nr):
        return False

    @property
    def last_round_number(self):
        return self.round_number


class MockShipFile(object):
    def __init__(self, mock_game_directory: MockGameDirectory):
        self.gd = mock_game_directory
        self.sf = ShipFile(self.gd, original_ship_file)
        self.ships = None

    @property
    def ship_lines(self):
        return self.sf.ship_lines

    def save(self, ships: list):
        """The roster is written back to disk in a real game; nothing to do here."""


class TestGames2(unittest.TestCase):
    def setUp(self):
        deactivate_logger_blocklist()

    @staticmethod
    def _setup_game() -> Game:
        gd = MockGameDirectory()
        return setup_game(gd, MockShipFile(gd))

    def _run(self, game: Game, nr_of_rounds: int):
        for i in range(1, nr_of_rounds + 1):
            game.init_round(i)
            self.assertTrue(game.current_round_ready)
            game.process_current_round()

    def test_game_2(self):
        """Same shape as test_game_1, but with two launchers firing rather than one.

        Scores the shield break and the kill. The total is not one sum: see test_game_1.
        """
        game = self._setup_game()
        target = game._dir.load_current_world().objects[ship_2_name]
        shield = target.defense[0]
        self.assertGreater(shield.strengths['W'], 0)
        without_shield_damage = shield.shield_break_score + target.hull + target.kill_score

        number_of_rounds = 1
        self._run(game, number_of_rounds)

        self.assertEqual(game._dir.last_round_number, number_of_rounds)
        final = game._dir.load_current_world()
        ships_1 = final.objects
        wreck = final.graveyard[ship_2_name]

        self.assertNotIn(ship_2_name, ships_1)
        self.assertEqual(0, wreck.defense[0].strengths['W'])
        self.assertGreater(ships_1[ship_1_name].score, without_shield_damage)



