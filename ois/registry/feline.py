from cfg import max_scan
from ois.ship import ShipType
from ois.registry.missiles import Rocket, Splinter, NanoMissile
from ois.registry.mines import SplinterMine
from comp.defense import Shields
from comp.launcher import Launcher
from comp.laser import Laser
from comp.ecm import Cloak
from comp.scanner import Gravscan


class F2551(ShipType):
    max_speed = 50
    max_turn = 50
    max_delta_v = 30
    max_hull = 75
    start_battery = 90
    generators = 8
    max_scan_distance = max_scan(30)

    @property
    def class_name(self):
        return "Tiger"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 110, 'E': 100, 'S': 100, 'W': 100}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 150),
            Laser('L2', 150),
            Launcher('R1', Rocket(), 10),
            Launcher('R2', Rocket(), 10),
            Launcher('M1', SplinterMine(), 10),
            Gravscan('G')
        ]

    @property
    def ecm(self):
        return [
            Cloak('Cloak', 0.25),
        ]


class F2547(ShipType):
    max_speed = 50
    max_turn = 45
    max_delta_v = 25
    max_hull = 80
    start_battery = 90
    generators = 8
    max_scan_distance = max_scan(30)

    @property
    def class_name(self):
        return "Panther"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 110, 'E': 100, 'S': 100, 'W': 100}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 130),
            Launcher('S1', Splinter(), 3, (270, 90)),
            Launcher('N1', NanoMissile(), 3, (270, 90)),
            Launcher('R1', Rocket(), 10),
            Launcher('R2', Rocket(), 10),
            Launcher('M1', SplinterMine(), 10),
            Gravscan('G')
        ]

    @property
    def ecm(self):
        return [
            Cloak('Cloak', 0.25),
        ]


class F2534(ShipType):
    max_speed = 55
    max_turn = 50
    max_delta_v = 30
    max_hull = 75
    start_battery = 90
    generators = 8
    max_scan_distance = max_scan(30)

    @property
    def class_name(self):
        return "Cheetah"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 100, 'E': 100, 'S': 100, 'W': 100}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 100),
            Launcher('S1', Splinter(), 5),
            Launcher('N1', NanoMissile(), 5),
            Launcher('R1', Rocket(), 20),
            Launcher('M1', SplinterMine(), 10),
            Gravscan('G')
        ]

    @property
    def ecm(self):
        return [
            Cloak('Cloak', 0.25),
        ]


class F2533(ShipType):
    max_speed = 45
    max_turn = 40
    max_delta_v = 20
    max_hull = 90
    start_battery = 80
    generators = 6
    max_scan_distance = max_scan(45)

    @property
    def class_name(self):
        return "Lion"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 100, 'E': 100, 'S': 100, 'W': 100}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 50),
            Launcher('S1', Splinter(), 4),
            Launcher('S2', Splinter(), 3, (315, 45)),
            Launcher('N1', NanoMissile(), 7, (315, 45)),
            Launcher('R1', Rocket(), 20),
            Launcher('M1', SplinterMine(), 10),
            Gravscan('G')
        ]

    @property
    def ecm(self):
        return [
            Cloak('Cloak', 0.25),
        ]
