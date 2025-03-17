"""
     Name  Type Faction Player   X Y
Blaster-1 H2545     One  Serge   1 0
 Shaper-1 H2552     Two  Serge 122 0

Blaster-1 Round 1 Commands:

1: Fire S1 90
1: Fire R1 90
1: Fire R1 90
2: Fire S1 90
2: Fire R1 90
2: Fire R1 90

Shaper-1 Round 1 Commands:

None
"""

import unittest
from collections import defaultdict

from arena.engine.command import parse_commands, CommandSet
from arena.engine.objects.objectinspace import Point
from arena.engine.objects.registry.builder import create
from arena.engine.round import GameRound
from arena.engine.objects.components.control import Pilot, Gunner, TargetingMode


class GameDirectoryStub(object):
    def __init__(self):
        self.ships = dict()
        self.init()

    def _create_ship(self, name, type_name, position, faction, player):
        ship = create(name, type_name, position)
        ship.faction = faction
        ship.player = player
        self.ships[name] = ship
        ship.speed = 10

    def init(self):
        self._create_ship("Blaster", "H2545", (1, 0), "One", "Blaster's Player")
        self._create_ship("Shaper", "H2552", (122, 0), "Two", "Shaper's Player")

    def commands(self):
        return """
            1: Fire S1 90
            1: Fire R1 90
            2: A10
            2: Fire S1 90
            2: Fire R1 90
        """


class TestGameOne(unittest.TestCase):
    def setUp(self):
        self.stub = GameDirectoryStub()
        self.objects = self.stub.ships
        self.game_round = GameRound(self.objects, 1)
        commands = [line.strip() for line in self.stub.commands().splitlines()]
        self.commands = {
            'Blaster': parse_commands(commands, self.objects['Blaster'], self.objects),
            'Shaper': {}
        }

    def test_round(self):
        self.game_round.do_round(self.commands)
        self.assertEqual(Point(1, 90), self.objects['Blaster'].pos)

    def test_control(self):
        pilot = Pilot()
        gunner = Gunner()
        control_components = [pilot, gunner]
        blaster = self.objects['Blaster']
        blaster.control = {comp.name: comp for comp in control_components}
        blaster._attach_components(control_components)
        pilot.set_current_target('Shaper')
        gunner.set_targeting_mode(TargetingMode.Offensive)

        self.game_round.do_round(self.commands)
        for t, events in blaster.history.events_per_tick.items():
            for event in events:
                print(t.tick, str(event))




if __name__ == '__main__':
    unittest.main()
