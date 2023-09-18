from cfg import max_scan
from ois.ship import ShipType
from ois.registry.missiles import Rocket, Splinter, NanoMissile
from ois.registry.mines import SplinterMine, NanocyteMine
from comp.defense import Shields
from comp.launcher import Launcher
from comp.laser import Laser
from comp.scanner import Gravscan


class I2544(ShipType):
    max_speed = 30
    max_turn = 25
    max_delta_v = 15
    max_hull = 150
    start_battery = 70
    generators = 6
    max_scan_distance = max_scan(45)

    @property
    def class_name(self):
        return "Hive"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 140, 'E': 140, 'S': 140, 'W': 140}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 100),
            Launcher('SA1', Splinter(), 5),
            Launcher('SF1', Splinter(), 5, (270, 90)),
            Launcher('SF2', Splinter(), 5, (270, 90)),
            Launcher('R1', Rocket(), 10),
            Launcher('N1', NanoMissile(), 5),
            Launcher('M1', SplinterMine(), 10),
            Gravscan('G')
        ]


class I2552(ShipType):
    max_speed = 25
    max_turn = 20
    max_delta_v = 10
    max_hull = 180
    start_battery = 80
    generators = 6
    max_scan_distance = max_scan(40)

    @property
    def class_name(self):
        return "Swarm"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 160, 'E': 150, 'S': 150, 'W': 150}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 110),
            Launcher('S1', Splinter(), 10),
            Launcher('SF1', Splinter(), 10, (315, 45)),
            Launcher('SF2', Splinter(), 5, (270, 90)),
            Launcher('R1', Rocket(), 10),
            Launcher('RF1', Rocket(), 10, (315, 45)),
            Launcher('N1', NanoMissile(), 10, (315, 45)),
            Launcher('M1', SplinterMine(), 10),
            Gravscan('G')
        ]


class I2526(ShipType):
    max_speed = 30
    max_turn = 30
    max_delta_v = 15
    max_hull = 150
    start_battery = 90
    generators = 6
    max_scan_distance = max_scan(45)

    @property
    def class_name(self):
        return "Colony"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 260, 'E': 125, 'S': 50, 'W': 125}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 150, (315, 45)),
            Launcher('S1', Splinter(), 6, (315, 45)),
            Launcher('S2', Splinter(), 6, (315, 45)),
            Launcher('S3', Splinter(), 6, (315, 45)),
            Launcher('S4', Splinter(), 6, (315, 45)),
            Launcher('N1', NanoMissile(), 12, (315, 45)),
            Launcher('R1', Rocket(), 20),
            Launcher('M1', SplinterMine(), 10),
            Gravscan('G')
        ]
