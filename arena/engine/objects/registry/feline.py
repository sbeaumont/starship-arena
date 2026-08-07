"""The raiding line: fast, thin, agile, and stealthy but not as stealthy as the snake.

Turning at 40 to 50 they can afford the narrowest arcs in the fleet, which is how their speed pays
for itself: a Cheetah brings a bow gun round in three ticks where a Swarm needs eight. They carry a
few mines to place where you will be, which is a different job from laying a field.
"""

from arena.cfg import max_scan
from arena.engine.objects.ship import ShipType
from arena.engine.objects.registry.missiles import Rocket, Splinter, NanoMissile
from arena.engine.objects.registry.mines import SplinterMine
from arena.engine.objects.components.defense import Shields
from arena.engine.objects.components.launcher import Launcher
from arena.engine.objects.components.laser import Laser
from arena.engine.objects.components.ecm import Cloak
from arena.engine.objects.components.scanner import Gravscan


class F2534(ShipType):
    max_speed = 60
    max_turn = 50
    max_delta_v = 30
    max_hull = 70
    start_battery = 95
    generators = 8
    max_scan_distance = max_scan(26)

    @property
    def class_name(self):
        return "Cheetah"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 100, 'E': 85, 'S': 70, 'W': 85}),
        ]

    @property
    def weapons(self):
        # Two tubes of ten rather than one of twenty: a launcher fires once a tick, so a single
        # deep tube leaves half its rounds unreachable inside a round.
        return [
            Laser('L1', 170, 60, (330, 30)),
            Launcher('R1', Rocket(), 10, (315, 45)),
            Launcher('R2', Rocket(), 10, (315, 45)),
            Launcher('M1', SplinterMine(), 3),
            Gravscan('G')
        ]

    @property
    def ecm(self):
        return [
            Cloak('C1', 6),
        ]


class F2551(ShipType):
    max_speed = 50
    max_turn = 50
    max_delta_v = 30
    max_hull = 85
    start_battery = 100
    generators = 8
    max_scan_distance = max_scan(30)

    @property
    def class_name(self):
        return "Tiger"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 120, 'E': 95, 'S': 80, 'W': 95}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 190, 65, (330, 30)),
            Laser('L2', 140, 55, (300, 60)),
            Launcher('S1', Splinter(), 5, (315, 45)),
            Launcher('R1', Rocket(), 8, (315, 45)),
            Launcher('M1', SplinterMine(), 3),
            Gravscan('G')
        ]

    @property
    def ecm(self):
        return [
            Cloak('C1', 6),
        ]


class F2547(ShipType):
    max_speed = 50
    max_turn = 45
    max_delta_v = 25
    max_hull = 85
    start_battery = 95
    generators = 7
    max_scan_distance = max_scan(32)

    @property
    def class_name(self):
        return "Panther"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 110, 'E': 90, 'S': 80, 'W': 90}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 150, 60, (315, 45)),
            Launcher('S1', Splinter(), 6, (330, 30)),
            Launcher('S2', Splinter(), 6, (330, 30)),
            Launcher('N1', NanoMissile(), 5, (300, 60)),
            Launcher('R1', Rocket(), 8, (315, 45)),
            Launcher('M1', SplinterMine(), 4),
            Gravscan('G')
        ]

    @property
    def ecm(self):
        return [
            Cloak('C1', 6),
        ]


class F2533(ShipType):
    max_speed = 45
    max_turn = 40
    max_delta_v = 25
    max_hull = 110
    start_battery = 100
    generators = 7
    max_scan_distance = max_scan(38)

    @property
    def class_name(self):
        return "Lion"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 130, 'E': 105, 'S': 90, 'W': 105}),
        ]

    @property
    def weapons(self):
        # The one Feline that fights across a beam instead of down the bow. At turn 40 a 120
        # degree broadside comes round in three ticks, which is a flanker rather than a fortress.
        return [
            Laser('L1', 160, 70, (300, 60)),
            Launcher('S1', Splinter(), 8, (30, 150)),
            Launcher('S2', Splinter(), 8, (210, 330)),
            Launcher('N1', NanoMissile(), 6, (315, 45)),
            Launcher('R1', Rocket(), 10, (315, 45)),
            Launcher('M1', SplinterMine(), 5),
            Gravscan('G')
        ]

    @property
    def ecm(self):
        return [
            Cloak('C1', 6),
        ]
