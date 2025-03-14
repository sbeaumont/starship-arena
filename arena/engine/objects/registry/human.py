from arena.cfg import max_scan
from arena.engine.objects.ship import ShipType
from arena.engine.objects.registry.missiles import Rocket, Splinter, NanoMissile, EMPMissile
from arena.engine.objects.registry.mines import SplinterMine, NanocyteMine
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
    start_battery = 125
    generators = 8
    max_scan_distance = max_scan(30)

    @property
    def class_name(self):
        return "Cairo"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 150, 'E': 100, 'S': 130, 'W': 100}),
        ]

    @property
    def weapons(self) -> list:
        return [
            Laser('L1', 180),
            Launcher('S1', Splinter(), 4, (270, 90)),
            Launcher('R1', Rocket(), 10),
            Launcher('R2', Rocket(), 10),
            Launcher('M1', SplinterMine(), 10),
            Launcher('E1', EMPMissile(), 5),
            Gravscan('G')
        ]


class H2552(ShipType):
    max_speed = 40
    max_turn = 35
    max_delta_v = 20
    max_hull = 110
    start_battery = 100
    generators = 7
    max_scan_distance = max_scan(35)

    @property
    def class_name(self):
        return "Babylon"

    @property
    def weapons(self):
        return [
            Laser('L1', 180, (270, 90)),
            Launcher('S1', Splinter(), 10, (90, 270)),
            Launcher('R1', Rocket(), 15),
            Launcher('N1', NanocyteMine(), 10),
            Gravscan('G')
        ]

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 150, 'E': 130, 'S': 140, 'W': 130}),
        ]

    @property
    def ecm(self):
        return [
            Cloak('C1', 0.2),
        ]


class H2535(ShipType):
    max_speed = 30
    max_turn = 30
    max_delta_v = 15
    max_hull = 150
    start_battery = 60
    generators = 5
    max_scan_distance = max_scan(50)

    @property
    def class_name(self):
        return "Rome"

    @property
    def weapons(self):
        return [
            Launcher('SS1', Splinter(), 10, (0, 180)),
            Launcher('SS2', Splinter(), 10, (0, 180)),
            Launcher('SP1', Splinter(), 10, (180, 0)),
            Launcher('SP2', Splinter(), 10, (180, 0)),
            Launcher('R1', Rocket(), 10),
            Launcher('N1', NanoMissile(), 10, (315, 45)),
            Gravscan('G')
        ]

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 100, 'E': 100, 'S': 100, 'W': 100}),
        ]

    @property
    def ecm(self):
        return [
            Cloak('Cloak', 0.2),
        ]


class H2527(ShipType):
    max_speed = 45
    max_turn = 40
    max_delta_v = 20
    max_hull = 100
    start_battery = 90
    generators = 8
    max_scan_distance = max_scan(35)

    @property
    def class_name(self):
        return "Athens"

    @property
    def weapons(self):
        return [
            Laser('L1', 180),
            Laser('L2', 180),
            Launcher('R1', Rocket(), 8),
            Launcher('R2', Rocket(), 8),
            Gravscan('G')
        ]

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 100, 'E': 100, 'S': 100, 'W': 100}),
        ]

    @property
    def ecm(self):
        return [
            Cloak('Cloak', 0.2),
        ]


