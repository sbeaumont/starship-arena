import unittest
from arena.engine.admin import GameSetup, distribute_factions
from arena.engine.gamedirectory import GameDirectory, ShipFile

original_ship_file = """Name           Type   Faction   Player     X   Y
Blaster        H2545  One       Serge   -400   0
Shaper         H2552  Two       Piet     400   0
Starbase-1     SB2531 One       Serge   -430   0"""


original_ship_file_without_coordinates = """Name           Type   Faction   Player
Blaster        H2545  One       Serge
Shaper         H2552  Two       Piet
Starbase-1     SB2531 One       Serge"""


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.gd = GameDirectory('test/test-games', 'test-game-2')
        self.gs1 = GameSetup(self.gd, ShipFile(self.gd, original_ship_file))
        self.gs2 = GameSetup(self.gd, ShipFile(self.gd, original_ship_file_without_coordinates))

    def test_dont_screw_up_ship_file(self):
        original = [line.split() for line in original_ship_file.splitlines()]
        new = [line.split() for line in self.gs1.shipfile.ship_file_with_coordinates(self.gs1.ships.values())]
        for pair in zip(original, new):
            self.assertEqual(pair[0], pair[1])

    def test_add_coords_to_ship_file(self):
        original = [line.split() for line in original_ship_file_without_coordinates.splitlines()]
        new = [line.split() for line in self.gs2.shipfile.ship_file_with_coordinates(self.gs2.ships.values())]
        for pair in zip(original, new):
            self.assertEqual(len(pair[0]), 4)
            self.assertEqual(len(pair[1]), 6)

    def test_distribute_ships(self):
        distribute_factions(self.gs2.ships.values(), 100)
        new = [line.split() for line in self.gs2.shipfile.ship_file_with_coordinates(self.gs2.ships.values())]
        for line in new[1:]:
            self.assertNotEqual(int(line[-1]), 0)
            self.assertNotEqual(int(line[-2]), 0)


if __name__ == '__main__':
    unittest.main()
