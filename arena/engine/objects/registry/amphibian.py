"""The standoff line: the longest eyes in the fleet and the heaviest guided warheads.

PowerSplinter is theirs, and until the payload airframe varies their reach is scan range rather
than missile range: they find you first, fire on a wide forward arc, and never have to close.
"""

from arena.cfg import max_scan
from arena.engine.objects.ship import ShipType
from arena.engine.objects.registry.missiles import Rocket, NanoMissile, PowerSplinter
from arena.engine.objects.registry.mines import SplinterMine
from arena.engine.objects.components.defense import Shields
from arena.engine.objects.components.launcher import Launcher
from arena.engine.objects.components.laser import Laser
from arena.engine.objects.components.ecm import Cloak
from arena.engine.objects.components.scanner import Gravscan


class A2545(ShipType):
    max_speed = 40
    max_turn = 30
    max_delta_v = 20
    max_hull = 150
    start_battery = 90
    generators = 6
    max_scan_distance = max_scan(55)

    @property
    def class_name(self):
        return "Terrapin"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 120, 'E': 115, 'S': 105, 'W': 115}),
        ]

    @property
    def weapons(self):
        # The furthest seeing hull in the game and no gun at all: everything it does, it does at
        # the far end of a missile flight.
        return [
            Launcher('P1', PowerSplinter(), 8, (270, 90)),
            Launcher('P2', PowerSplinter(), 8, (270, 90)),
            Launcher('N1', NanoMissile(), 10, (270, 90)),
            Launcher('R1', Rocket(), 10, (315, 45)),
            Launcher('M1', SplinterMine(), 8),
            Gravscan('G')
        ]


class A2527(ShipType):
    max_speed = 45
    max_turn = 35
    max_delta_v = 25
    max_hull = 105
    start_battery = 90
    generators = 7
    max_scan_distance = max_scan(42)

    @property
    def class_name(self):
        return "Alligator"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 115, 'E': 100, 'S': 90, 'W': 100}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 150, 70, (300, 60)),
            Launcher('P1', PowerSplinter(), 6, (300, 60)),
            Launcher('N1', NanoMissile(), 6, (300, 60)),
            Launcher('R1', Rocket(), 10, (315, 45)),
            Launcher('M1', SplinterMine(), 8),
            Gravscan('G')
        ]


class A2539(ShipType):
    max_speed = 45
    max_turn = 35
    max_delta_v = 25
    max_hull = 100
    start_battery = 100
    generators = 7
    max_scan_distance = max_scan(38)

    @property
    def class_name(self):
        return "Caiman"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 110, 'E': 100, 'S': 90, 'W': 100}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 140, 75, (330, 30)),
            Laser('L2', 110, 65, (270, 90)),
            Launcher('P1', PowerSplinter(), 6, (300, 60)),
            Launcher('P2', PowerSplinter(), 6, (300, 60)),
            Launcher('R1', Rocket(), 8, (315, 45)),
            Launcher('M1', SplinterMine(), 8),
            Gravscan('G')
        ]

    @property
    def ecm(self):
        return [
            Cloak('C1', 5),
        ]


class A2553(ShipType):
    max_speed = 45
    max_turn = 40
    max_delta_v = 25
    max_hull = 85
    start_battery = 95
    generators = 7
    max_scan_distance = max_scan(35)

    @property
    def class_name(self):
        return "Frog"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 105, 'E': 90, 'S': 80, 'W': 90}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 160, 65, (315, 45)),
            Launcher('P1', PowerSplinter(), 6, (315, 45)),
            Launcher('N1', NanoMissile(), 5, (315, 45)),
            Launcher('R1', Rocket(), 8, (315, 45)),
            Launcher('M1', SplinterMine(), 6),
            Gravscan('G')
        ]

    @property
    def ecm(self):
        return [
            Cloak('C1', 5),
        ]