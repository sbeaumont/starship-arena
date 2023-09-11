from cfg import max_scan
from ois.ship import ShipType
from ois.registry.missiles import Rocket, NanoMissile, PowerSplinter
from ois.registry.mines import SplinterMine
from comp.defense import Shields
from comp.launcher import Launcher
from comp.laser import Laser
from comp.ecm import Cloak
from comp.scanner import Gravscan


class A2527(ShipType):
    max_speed = 45
    max_turn = 35
    max_delta_v = 25
    max_hull = 100
    start_battery = 60
    generators = 7
    max_scan_distance = max_scan(35)

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 100, 'E': 100, 'S': 100, 'W': 100}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 140),
            Launcher('S1', PowerSplinter(), 5),
            Launcher('N1', NanoMissile(), 5, (315, 45)),
            Launcher('R1', Rocket(), 10),
            Launcher('RF1', Rocket(), 12, (315, 45)),
            Launcher('M1', SplinterMine(), 10),
            Gravscan('G')
        ]


class A2539(ShipType):
    max_speed = 45
    max_turn = 35
    max_delta_v = 25
    max_hull = 100
    start_battery = 80
    generators = 7
    max_scan_distance = max_scan(30)

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 100, 'E': 100, 'S': 100, 'W': 100}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 110),
            Laser('LF1', 110, (315, 45)),
            Launcher('S1', PowerSplinter(), 5),
            Launcher('SF1', PowerSplinter(), 5, (315, 45)),
            Launcher('N1', NanoMissile(), 10),
            Launcher('R1', Rocket(), 5),
            Launcher('RF1', Rocket(), 5, (315, 45)),
            Launcher('M1', SplinterMine(), 10),
            Gravscan('G')
        ]

    @property
    def ecm(self):
        return [
            Cloak('Cloak', 0.20),
        ]


class A2545(ShipType):
    max_speed = 40
    max_turn = 30
    max_delta_v = 20
    max_hull = 150
    start_battery = 80
    generators = 5
    max_scan_distance = max_scan(45)

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 110, 'E': 110, 'S': 110, 'W': 110}),
        ]

    @property
    def weapons(self):
        return [
            Launcher('S1', PowerSplinter(), 6),
            Launcher('S2', PowerSplinter(), 6),
            Launcher('SF1', PowerSplinter(), 6, (270, 90)),
            Launcher('N1', NanoMissile(), 12, (270, 90)),
            Launcher('R1', Rocket(), 8),
            Launcher('RF1', Rocket(), 12, (270, 90)),
            Launcher('M1', SplinterMine(), 10),
            Gravscan('G')
        ]


class A2553(ShipType):
    max_speed = 40
    max_turn = 40
    max_delta_v = 20
    max_hull = 80
    start_battery = 70
    generators = 6
    max_scan_distance = max_scan(40)

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 100, 'E': 100, 'S': 100, 'W': 100}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 120),
            Launcher('S1', PowerSplinter(), 5),
            Launcher('SF1', PowerSplinter(), 5, (315, 45)),
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


