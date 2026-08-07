"""The fortress line: slow, thick, many-tubed, and the only line with no cloak on any hull.

Turning at 20 to 30 they cannot have narrow arcs at all, so their guns fire across a beam and their
identity is holding ground: broadsides, deep magazines, and mine fields rather than placements.
"""

from arena.cfg import max_scan
from arena.engine.objects.ship import ShipType
from arena.engine.objects.registry.missiles import Rocket, Splinter, NanoMissile
from arena.engine.objects.registry.mines import SplinterMine
from arena.engine.objects.components.defense import Shields
from arena.engine.objects.components.launcher import Launcher
from arena.engine.objects.components.laser import Laser
from arena.engine.objects.components.scanner import Gravscan


class I2544(ShipType):
    max_speed = 30
    max_turn = 25
    max_delta_v = 15
    max_hull = 150
    start_battery = 80
    generators = 7
    max_scan_distance = max_scan(45)

    @property
    def class_name(self):
        return "Hive"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 145, 'E': 140, 'S': 125, 'W': 140}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 120, 75, (300, 60)),
            Launcher('SS1', Splinter(), 6, (30, 150)),
            Launcher('SP1', Splinter(), 6, (210, 330)),
            Launcher('R1', Rocket(), 8, (270, 90)),
            Launcher('M1', SplinterMine(), 15),
            Gravscan('G')
        ]


class I2552(ShipType):
    max_speed = 25
    max_turn = 20
    max_delta_v = 10
    max_hull = 185
    start_battery = 85
    generators = 6
    max_scan_distance = max_scan(40)

    @property
    def class_name(self):
        return "Swarm"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 165, 'E': 155, 'S': 145, 'W': 155}),
        ]

    @property
    def weapons(self):
        # Twenty mines is the deepest field in the game, and at speed 25 laying it is most of what
        # this hull does with a round.
        return [
            Laser('L1', 110, 75, (270, 90)),
            Launcher('SS1', Splinter(), 8, (30, 150)),
            Launcher('SP1', Splinter(), 8, (210, 330)),
            Launcher('N1', NanoMissile(), 8, (270, 90)),
            Launcher('M1', SplinterMine(), 20),
            Gravscan('G')
        ]


class I2526(ShipType):
    max_speed = 30
    max_turn = 30
    max_delta_v = 15
    max_hull = 150
    start_battery = 95
    generators = 6
    max_scan_distance = max_scan(45)

    @property
    def class_name(self):
        return "Colony"

    @property
    def defense(self):
        # Everything on the bow. The one hull in the fleet that genuinely cannot afford to be
        # caught from astern, and it knows it.
        return [
            Shields('Shields', {'N': 260, 'E': 120, 'S': 60, 'W': 120}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 150, 70, (315, 45)),
            Launcher('S1', Splinter(), 6, (300, 60)),
            Launcher('S2', Splinter(), 6, (300, 60)),
            Launcher('S3', Splinter(), 6, (300, 60)),
            Launcher('N1', NanoMissile(), 10, (300, 60)),
            Launcher('R1', Rocket(), 10, (315, 45)),
            Launcher('M1', SplinterMine(), 12),
            Gravscan('G')
        ]