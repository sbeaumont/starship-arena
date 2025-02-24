from arena_engine.ois.ship import ShipType
from cfg import max_scan
from arena_engine.ois.starbase import Starbase
from arena_engine.ois.registry.missiles import Rocket, Splinter
from arena_engine.ois.comp.defense import Shields
from arena_engine.ois.comp.launcher import Launcher
from arena_engine.ois.comp.laser import Laser
from arena_engine.ois.comp.scanner import Gravscan


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
            Launcher('R2', Rocket(), 75),
            Gravscan('G')
        ]
