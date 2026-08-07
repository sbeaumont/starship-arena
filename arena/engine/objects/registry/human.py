"""The attrition line: EMP and nanocytes, which are the kit for taking something apart.

Strip a face and then convert it. Human hulls are the generalists of the fleet, and the one thing
they own outright is ordnance that does nothing to a hull and everything to what is left of one.
Cloak belongs to the snakes now, so only Babylon carries one.
"""

from arena.cfg import max_scan
from arena.engine.objects.ship import ShipType
from arena.engine.objects.registry.missiles import Rocket, Splinter, NanoMissile, EMPMissile
from arena.engine.objects.registry.mines import NanocyteMine
from arena.engine.objects.components.defense import Shields
from arena.engine.objects.components.launcher import Launcher
from arena.engine.objects.components.laser import Laser
from arena.engine.objects.components.ecm import Cloak
from arena.engine.objects.components.scanner import Gravscan


class H2545(ShipType):
    max_speed = 45
    max_turn = 35
    max_delta_v = 25
    max_hull = 100
    start_battery = 120
    generators = 7
    max_scan_distance = max_scan(30)

    @property
    def class_name(self):
        return "Cairo"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 140, 'E': 105, 'S': 95, 'W': 105}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 150, 70, (315, 45)),
            Launcher('E1', EMPMissile(), 6, (300, 60)),
            Launcher('R1', Rocket(), 10, (315, 45)),
            Launcher('M1', NanocyteMine(), 8),
            Gravscan('G')
        ]


class H2552(ShipType):
    max_speed = 40
    max_turn = 35
    max_delta_v = 20
    max_hull = 115
    start_battery = 110
    generators = 7
    max_scan_distance = max_scan(35)

    @property
    def class_name(self):
        return "Babylon"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 140, 'E': 125, 'S': 115, 'W': 125}),
        ]

    @property
    def weapons(self):
        # The whole attrition kit on one hull: EMP forward to strip a face, nanocytes behind it,
        # and the deepest nanocyte field in the game.
        return [
            Laser('L1', 160, 70, (270, 90)),
            Launcher('E1', EMPMissile(), 8, (300, 60)),
            Launcher('S1', Splinter(), 8, (90, 270)),
            Launcher('M1', NanocyteMine(), 12),
            Gravscan('G')
        ]

    @property
    def ecm(self):
        return [
            Cloak('C1', 5),
        ]


class H2535(ShipType):
    max_speed = 30
    max_turn = 30
    max_delta_v = 15
    max_hull = 155
    start_battery = 80
    generators = 6
    max_scan_distance = max_scan(50)

    @property
    def class_name(self):
        return "Rome"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 115, 'E': 110, 'S': 100, 'W': 110}),
        ]

    @property
    def weapons(self):
        # Forty splinters and not one laser. The only gunless hull in the fleet, and it reads that
        # way at the table.
        return [
            Launcher('SS1', Splinter(), 10, (30, 150)),
            Launcher('SS2', Splinter(), 10, (30, 150)),
            Launcher('SP1', Splinter(), 10, (210, 330)),
            Launcher('SP2', Splinter(), 10, (210, 330)),
            Launcher('N1', NanoMissile(), 8, (300, 60)),
            Launcher('M1', NanocyteMine(), 10),
            Gravscan('G')
        ]


class H2527(ShipType):
    max_speed = 45
    max_turn = 40
    max_delta_v = 20
    max_hull = 100
    start_battery = 110
    generators = 8
    max_scan_distance = max_scan(35)

    @property
    def class_name(self):
        return "Athens"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 120, 'E': 95, 'S': 85, 'W': 95}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 200, 70, (330, 30)),
            Laser('L2', 200, 70, (330, 30)),
            Launcher('E1', EMPMissile(), 4, (300, 60)),
            Launcher('R1', Rocket(), 8, (315, 45)),
            Gravscan('G')
        ]