import shutil
import tempfile
import unittest

from arena.engine.admin import GameSetup
from arena.engine.gamedirectory import GameDirectory, ShipFile

PLACED = [
    {'name': 'Blaster', 'type': 'H2545', 'faction': 'One', 'player': 'Serge',
     'x': -400, 'y': 0, 'heading': 90},
    {'name': 'Shaper', 'type': 'H2552', 'faction': 'Two', 'player': 'Piet',
     'x': 400, 'y': 0, 'heading': 270},
    {'name': 'Starbase-1', 'type': 'SB2531', 'faction': 'One', 'player': 'Serge',
     'x': -430, 'y': 0, 'heading': 90},
]


class TestTheRosterSurvivesSetup(unittest.TestCase):
    """The roster says where everything starts, and setup writes back what it was given."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.gd = GameDirectory(self.root, 'game')
        self.gd.setup_directories()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _save_and_reload(self, setup: GameSetup) -> dict:
        setup.shipfile.save(setup.ships.values())
        return {line.name: line for line in ShipFile(self.gd).ship_lines}

    def test_what_the_roster_gave_comes_back_unchanged(self):
        setup = GameSetup(self.gd, ShipFile(self.gd, PLACED))

        saved = self._save_and_reload(setup)

        for ship in PLACED:
            self.assertEqual(ship['x'], saved[ship['name']].x)
            self.assertEqual(ship['y'], saved[ship['name']].y)
            self.assertEqual(ship['heading'], saved[ship['name']].heading)
            self.assertEqual(ship['player'], saved[ship['name']].player)

    def test_a_ship_starts_facing_the_way_the_roster_says(self):
        setup = GameSetup(self.gd, ShipFile(self.gd, PLACED))

        for ship in PLACED:
            self.assertEqual(ship['heading'], setup.ships[ship['name']].heading)