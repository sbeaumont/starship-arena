import shutil
import tempfile
import unittest

from arena.engine.admin import GameSetup, distribute_factions
from arena.engine.gamedirectory import GameDirectory, ShipFile

PLACED = [
    {'name': 'Blaster', 'type': 'H2545', 'faction': 'One', 'player': 'Serge', 'x': -400, 'y': 0},
    {'name': 'Shaper', 'type': 'H2552', 'faction': 'Two', 'player': 'Piet', 'x': 400, 'y': 0},
    {'name': 'Starbase-1', 'type': 'SB2531', 'faction': 'One', 'player': 'Serge', 'x': -430, 'y': 0},
]

UNPLACED = [{k: v for k, v in ship.items() if k not in ('x', 'y')} for ship in PLACED]


class TestTheRosterSurvivesSetup(unittest.TestCase):
    """Setup writes coordinates back, so running it twice places the ships the same way."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.gd = GameDirectory(self.root, 'game')
        self.gd.setup_directories()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _save_and_reload(self, setup: GameSetup) -> dict:
        setup.shipfile.save(setup.ships.values())
        return {line.name: line for line in ShipFile(self.gd).ship_lines}

    def test_coordinates_that_were_given_come_back_unchanged(self):
        setup = GameSetup(self.gd, ShipFile(self.gd, PLACED))

        saved = self._save_and_reload(setup)

        for ship in PLACED:
            self.assertEqual(ship['x'], saved[ship['name']].x)
            self.assertEqual(ship['y'], saved[ship['name']].y)
            self.assertEqual(ship['player'], saved[ship['name']].player)

    def test_ships_without_coordinates_are_placed_and_the_places_are_kept(self):
        setup = GameSetup(self.gd, ShipFile(self.gd, UNPLACED))
        for ship in setup.ships.values():
            self.assertEqual((0, 0), (ship.pos.x, ship.pos.y))

        distribute_factions(setup.ships.values(), 100)
        saved = self._save_and_reload(setup)

        for name, line in saved.items():
            self.assertNotEqual((0, 0), (line.x, line.y), f"{name} was never placed")