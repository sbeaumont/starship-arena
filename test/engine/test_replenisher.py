"""A starbase restocks a ship alongside it: `Rep RP <ship>`."""
import os
import shutil
import tempfile
from unittest import TestCase

from arena.app.services import AdminService
from arena.engine.game import Game
from arena.engine.gamedirectory import GameDirectory
from arena.engine.objects.registry import builder

# A roster keeps the coordinates it is given and is turned to face the middle, so everything here
# starts pointing at the origin: a ship east of the base closes on it. Voyager sits 5 off the base
# and stays there. Passer starts 20 east and arrives at speed. The enemy is parked alongside too,
# because whose ship it is, is not a question the base asks.
ROSTER = [
    {'name': 'Base', 'type': 'SB2531', 'faction': 'One', 'player': 'Rik', 'x': 100, 'y': 0},
    {'name': 'Voyager', 'type': 'A2527', 'faction': 'One', 'player': 'Rik', 'x': 105, 'y': 0},
    {'name': 'Passer', 'type': 'A2527', 'faction': 'One', 'player': 'Rik', 'x': 120, 'y': 0},
    {'name': 'Enemy', 'type': 'H2552', 'faction': 'Two', 'player': 'Piet', 'x': 100, 'y': 5},
    {'name': 'Far', 'type': 'H2552', 'faction': 'Two', 'player': 'Piet', 'x': 600, 'y': 0},
]


class TestFiringTheReplenisher(TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.games = os.path.join(self.root, 'games')
        admin = AdminService(self.root)
        admin.issue_login('Rik')
        admin.create_game('replenish', ROSTER, 'generic')
        self.gd = GameDirectory(self.games, 'replenish')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _orders(self, ship: str, text: str):
        path = os.path.join(self.games, 'replenish', 'commands', f'{ship}-commands-1.txt')
        with open(path, 'w') as f:
            f.write(text)

    def _run(self, base_orders: str, **rest):
        for ship in ('Voyager', 'Passer', 'Enemy', 'Far'):
            self._orders(ship, rest.get(ship, ""))
        self._orders('Base', base_orders)
        Game(self.gd).process_current_round()
        return self.gd.load_current_world()

    @staticmethod
    def _said(ois) -> list:
        return [str(e) for th in ois.history.ticks.values() for e in th.events]

    def test_it_fills_a_ship_alongside(self):
        world = self._run("1: Rep RP Voyager\n")
        voyager = world.objects['Voyager']

        self.assertEqual(voyager._type.max_hull, voyager.hull)
        self.assertEqual(voyager._type.max_battery, voyager.battery)

    def test_it_says_so_on_both_sides(self):
        world = self._run("1: Rep RP Voyager\n")

        self.assertTrue(any('Replenished Voyager' in s for s in self._said(world.objects['Base'])))
        self.assertTrue(any('Replenished by Base' in s
                            for s in self._said(world.objects['Voyager'])))

    def test_it_restocks_the_other_side_too(self):
        """Collusion is a move, not a bug: the base is never asked whose ship it is."""
        world = self._run("1: Rep RP Enemy\n")

        self.assertTrue(any('Replenished Enemy' in s for s in self._said(world.objects['Base'])))

    def test_a_ship_out_of_reach_is_refused(self):
        world = self._run("1: Rep RP Far\n")

        self.assertTrue(any('beyond the 10 it reaches' in s
                            for s in self._said(world.objects['Base'])))

    def test_a_ship_going_too_fast_is_refused(self):
        """Passer ends the tick on top of the base, and still goes by."""
        world = self._run("1: Rep RP Passer\n", Passer="1: A20\n")

        self.assertTrue(any('too fast to hold' in s for s in self._said(world.objects['Base'])))

    def test_the_base_can_not_restock_itself(self):
        world = self._run("1: Rep RP Base\n")

        self.assertTrue(any('the base it is mounted on' in s
                            for s in self._said(world.objects['Base'])))

    def test_serving_a_ship_does_not_restock_the_base(self):
        world = self._run("1: Fire S1 90\n2: Rep RP Voyager\n")
        base = world.objects['Base']

        self.assertEqual(base._type.weapons[2].ammo - 1, base.weapons['S1'].ammo)

    def test_only_ships_are_offered(self):
        world = self.gd.load_current_world()
        world.add(builder.create('Rock', 'Asteroid', (100, 8)))
        ship_input = world.objects['Base'].weapons['RP'].expected_parameters[0]
        ship_input.set_world(world)

        self.assertEqual(['Enemy', 'Far', 'Passer', 'Voyager'], ship_input.choices,
                         "terrain has no faction, and the base is not offered itself")

    def test_it_reaches_ten(self):
        world = self.gd.load_current_world()

        self.assertEqual(10, world.objects['Base'].weapons['RP'].range)


class TestReplenishingAMachine(TestCase):
    """The reset is the machine's own: the base asks, the ship does it."""

    def test_a_boosted_quadrant_keeps_its_boost(self):
        """A restock tops you up. It never trades a boosted shield back down for its own maximum."""
        ship = builder.create('Voyager', 'A2527', (0, 0))
        boosted = ship.defense[0].max_strengths['N'] * 2
        ship.defense[0].strengths['N'] = boosted
        ship.defense[0].strengths['E'] = 0

        ship.replenish()

        self.assertEqual(boosted, ship.defense[0].strengths['N'])
        self.assertEqual(ship._type.defense[0].strengths['E'], ship.defense[0].strengths['E'],
                         "a spent quadrant still comes back")

    def test_a_battery_over_the_maximum_keeps_it(self):
        ship = builder.create('Voyager', 'A2527', (0, 0))
        ship.battery = ship._type.max_battery + 50

        ship.replenish()

        self.assertEqual(ship._type.max_battery + 50, ship.battery)

    def test_it_puts_hull_battery_and_components_back(self):
        ship = builder.create('Voyager', 'A2527', (0, 0))
        ship.hull = 1
        ship.battery = 0
        ship.defense[0].strengths['N'] = 0

        ship.replenish()

        self.assertEqual(ship._type.max_hull, ship.hull)
        self.assertEqual(ship._type.max_battery, ship.battery)
        self.assertEqual(ship._type.defense[0].strengths['N'], ship.defense[0].strengths['N'])