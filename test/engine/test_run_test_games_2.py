import unittest

from arena.engine.admin import setup_game
from arena.engine.game import Game
from arena.engine.gamedirectory import ShipFile
from arena.log import deactivate_logger_blocklist

ship_1_name = "Poodle"
ship_2_name = "PoodleII"


original_ship_file = f"""Name Type Faction Player X Y
{ship_1_name}        H2545  One       Serge   1   0
{ship_2_name}        H2552  Two       Piet    122 0"""

command_ship_1_1 = """
    1: Fire S1 45
    1: Fire R1 90
    1: Fire R1 90
    2: Fire S1 90
    2: Fire R1 90
    2: Fire R1 90
"""

commands = {
    (ship_1_name, 1): command_ship_1_1,
    (ship_2_name, 1): ''
}


class MockGameDirectory(object):
    class MockRoundDir(object):
        def __init__(self, round_nr: int):
            self.files = dict()
            self.round_nr = round_nr

        def save(self, name, contents, binary=False):
            self.files[name] = contents

        @property
        def full_name(self):
            return f'mock-round-{self.round_nr}'

    def __init__(self):
        self.path = ''
        self.ships = None
        self.round_number = 0
        self.graveyard = dict()
        self.round_dirs = dict()

    def setup_directories(self):
        pass

    def clean(self):
        pass

    @property
    def init_file(self) -> str:
        return 'mock_init_file_name'

    def save(self, obj, nr):
        self.round_number = nr

    def load_current_status(self):
        return self.ships

    def load_graveyard(self):
        return self.graveyard

    def save_graveyard(self, graveyard):
        self.graveyard = graveyard

    def load_status(self, round_nr: int):
        return self.ships

    def command_file_exists(self, ship_name, round_nr):
        return (ship_name, round_nr) in commands

    def read_command_file(self, ship_name, round_nr):
        return commands[(ship_name, round_nr)].splitlines()

    def status_file_for_round_exists(self, round_nr):
        return False

    @property
    def last_round_number(self):
        return self.round_number

    def round_dir(self, round_nr: int):
        if round_nr in self.round_dirs:
            return self.round_dirs[round_nr]
        else:
            rd = MockGameDirectory.MockRoundDir(round_nr)
            self.round_dirs[round_nr] = rd
            return rd


class MockShipFile(object):
    def __init__(self, mock_game_directory: MockGameDirectory):
        self.gd = mock_game_directory
        self.sf = ShipFile(self.gd, original_ship_file)
        self.ships = None

    @property
    def ship_lines(self):
        return self.sf.ship_lines

    def save(self, ships: list):
        self.gd.ships = {ship.name: ship for ship in ships}


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
            self.assertTrue(game.round_ready)
            game.do_round()

    def test_game_2(self):
        game = self._setup_game()
        ships_0 = game._dir.load_current_status()
        ship = ships_0[ship_2_name]
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
        self.assertEqual(total_score, ships_1[ship_1_name].score)
        self.assertIn(ship_2_name, game._dir.load_graveyard())
        round_files = game._dir.round_dir(1).files
        self.assertEqual(6, len(round_files))



