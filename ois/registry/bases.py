from ois.ship import ShipType
from cfg import max_scan
from ois.starbase import Starbase
from ois.registry.missiles import Rocket, Splinter
from comp.defense import Shields
from comp.launcher import Launcher
from comp.laser import Laser


class SB2531(ShipType):
    """Default starbase"""
    base_type = Starbase
    max_delta_v = 0
    max_speed = 0
    max_turn = 0
    generators = 12
    max_battery = 1000
    start_battery = 200
    max_hull = 250
    max_scan_distance = max_scan(65)
    max_replenish_distance = 10
    max_replenish_speed = 10

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 400, 'E': 400, 'S': 400, 'W': 400}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 300),
            Laser('L2', 300),
            Launcher('S1', Splinter(), 40),
            Launcher('S2', Splinter(), 40),
            Launcher('R1', Rocket(), 75),
            Launcher('R2', Rocket(), 75)
        ]
