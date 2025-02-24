from arena.cfg import max_scan
from arena.engine.objects.ship import ShipType
from arena.engine.objects.registry.missiles import Rocket, Splinter, NanoMissile
from arena.engine.objects.registry.mines import SplinterMine
from arena.engine import Shields
from arena.engine.objects.components.launcher import Launcher
from arena.engine import Laser
from arena.engine.objects.components.ecm import Cloak
from arena.engine import Gravscan


class R2545(ShipType):
    max_speed = 35
    max_turn = 30
    max_delta_v = 15
    max_hull = 110
    start_battery = 90
    generators = 7
    max_scan_distance = max_scan(35)

    @property
    def class_name(self):
        return "Komodo"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 120, 'E': 100, 'S': 100, 'W': 100}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 130),
            Launcher('S1', Splinter(), 10),
            Launcher('N1', NanoMissile(), 10),
            Launcher('R1', Rocket(), 8),
            Launcher('R2', Rocket(), 8),
            Launcher('M1', SplinterMine(), 10),
            Gravscan('G')
        ]


class R2525(ShipType):
    max_speed = 40
    max_turn = 35
    max_delta_v = 20
    max_hull = 80
    start_battery = 90
    generators = 7
    max_scan_distance = max_scan(30)

    @property
    def class_name(self):
        return "Viper"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 100, 'E': 100, 'S': 100, 'W': 100}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 120),
            Launcher('S1', Splinter(), 5),
            Launcher('N1', NanoMissile(), 5),
            Launcher('R1', Rocket(), 10),
            Launcher('M1', SplinterMine(), 10),
            Gravscan('G')
        ]

    @property
    def ecm(self):
        return [
            Cloak('Cloak', 0.20),
        ]


class R2531(ShipType):
    max_speed = 30
    max_turn = 25
    max_delta_v = 15
    max_hull = 150
    start_battery = 80
    generators = 5
    max_scan_distance = max_scan(45)

    @property
    def class_name(self):
        return "Dragon"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 120, 'E': 120, 'S': 120, 'W': 120}),
        ]

    @property
    def weapons(self):
        return [
            Launcher('S1', Splinter(), 5),
            Launcher('S2', Splinter(), 5),
            Launcher('S3', Splinter(), 5),
            Launcher('N1', NanoMissile(), 10),
            Launcher('R1', Rocket(), 10),
            Launcher('M1', SplinterMine(), 10),
            Gravscan('G')
        ]

    @property
    def ecm(self):
        return [
            Cloak('Cloak', 0.20),
        ]


class R2551(ShipType):
    max_speed = 35
    max_turn = 30
    max_delta_v = 15
    max_hull = 105
    start_battery = 90
    generators = 7
    max_scan_distance = max_scan(35)

    @property
    def class_name(self):
        return "Cobra"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 120, 'E': 100, 'S': 100, 'W': 100}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 80),
            Launcher('S1', Splinter(), 4),
            Launcher('S2', Splinter(), 4),
            Launcher('N1', NanoMissile(), 5),
            Launcher('R1', Rocket(), 10),
            Launcher('M1', SplinterMine(), 10),
            Gravscan('G')
        ]
