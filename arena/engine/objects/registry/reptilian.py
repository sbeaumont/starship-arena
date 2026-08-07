"""The ambush line: the best cloaks in the game, lasers as the alpha strike, and no mines at all.

Every gun points forward or across a beam, so a Reptilian has to choose its approach and commit to
it. Giving up area denial entirely is what makes the snake a different animal from the cat.
"""

from arena.cfg import max_scan
from arena.engine.objects.ship import ShipType
from arena.engine.objects.registry.missiles import Rocket, Splinter, NanoMissile
from arena.engine.objects.components.defense import Shields
from arena.engine.objects.components.launcher import Launcher
from arena.engine.objects.components.laser import Laser
from arena.engine.objects.components.ecm import Cloak
from arena.engine.objects.components.scanner import Gravscan


class R2525(ShipType):
    max_speed = 45
    max_turn = 45
    max_delta_v = 25
    max_hull = 80
    start_battery = 110
    generators = 8
    max_scan_distance = max_scan(28)

    @property
    def class_name(self):
        return "Viper"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 110, 'E': 80, 'S': 70, 'W': 80}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 200, 60, (330, 30)),
            Launcher('R1', Rocket(), 6, (315, 45)),
            Gravscan('G')
        ]

    @property
    def ecm(self):
        return [
            Cloak('C1', 3),
        ]


class R2545(ShipType):
    max_speed = 35
    max_turn = 35
    max_delta_v = 20
    max_hull = 115
    start_battery = 110
    generators = 7
    max_scan_distance = max_scan(32)

    @property
    def class_name(self):
        return "Komodo"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 140, 'E': 100, 'S': 80, 'W': 100}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 220, 70, (330, 30)),
            Laser('L2', 130, 55, (300, 60)),
            Launcher('S1', Splinter(), 6, (315, 45)),
            Launcher('R1', Rocket(), 8, (315, 45)),
            Gravscan('G')
        ]

    @property
    def ecm(self):
        return [
            Cloak('C1', 3),
        ]


class R2551(ShipType):
    max_speed = 40
    max_turn = 40
    max_delta_v = 25
    max_hull = 85
    start_battery = 120
    generators = 8
    max_scan_distance = max_scan(26)

    @property
    def class_name(self):
        return "Cobra"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 120, 'E': 75, 'S': 60, 'W': 75}),
        ]

    @property
    def weapons(self):
        # The hardest hitting gun in the fleet and the shortest ranged: 320 at contact, 135 at 20
        # units, nothing at 55. One pass decides the fight.
        return [
            Laser('L1', 320, 55, (345, 15)),
            Laser('L2', 120, 75, (315, 45)),
            Launcher('R1', Rocket(), 5, (315, 45)),
            Gravscan('G')
        ]

    @property
    def ecm(self):
        return [
            Cloak('C1', 3),
        ]


class R2531(ShipType):
    max_speed = 30
    max_turn = 25
    max_delta_v = 15
    max_hull = 160
    start_battery = 90
    generators = 6
    max_scan_distance = max_scan(45)

    @property
    def class_name(self):
        return "Dragon"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 130, 'E': 125, 'S': 110, 'W': 125}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 240, 60, (300, 60)),
            Launcher('S1', Splinter(), 8, (30, 150)),
            Launcher('S2', Splinter(), 8, (210, 330)),
            Launcher('R1', Rocket(), 8, (315, 45)),
            Gravscan('G')
        ]

    @property
    def ecm(self):
        return [
            Cloak('C1', 4),
        ]