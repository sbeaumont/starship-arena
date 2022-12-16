"""
Configurations of types of weapons and ships
"""

import sys
import inspect
from weapon import Laser, RocketLauncher
from history import History, ShipSnapshot, RocketSnapshot, StarbaseSnapshot
from objectinspace import Ship, Rocket, Starbase
from defense import Shields


def create(name: str, type_name: str, position: tuple, tick: int):
    """Return an instance of a ship type object by its class name."""
    type_classes = {c[0]: c[1] for c in inspect.getmembers(sys.modules[__name__], inspect.isclass)}
    type_instance = type_classes[type_name]()
    ois = type_instance.base_type(name, type_instance, position)
    ois.history = History(ois, type_instance.snapshot_type, tick)
    return ois


class Splinter(object):
    """Default rocket"""
    base_type = Rocket
    snapshot_type = RocketSnapshot
    max_speed = 60
    explode_distance = 6
    explode_damage = 10
    scan_cone = 45
    max_battery = 75
    hull = 1
    max_scan_distance = 150


class H2545(object):
    """Default space ship"""
    base_type = Ship
    snapshot_type = ShipSnapshot
    max_delta_v = 25
    max_speed = 45
    max_turn = 35
    generators = 8
    max_battery = 500
    start_battery = 125
    hull = 100
    max_scan_distance = 200

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 130, 'E': 100, 'S': 100, 'W': 100}),
        ]

    @property
    def weapons(self):
        return {
            'L1': Laser('L1'),
            'M1': RocketLauncher('M1', Splinter())
        }


class SB2531(object):
    """Default starbase"""
    base_type = Starbase
    snapshot_type = StarbaseSnapshot
    max_delta_v = 0
    max_speed = 0
    max_turn = 0
    generators = 12
    max_battery = 1000
    start_battery = 200
    hull = 250
    max_scan_distance = 400
    max_replenish_distance = 10
    max_replenish_speed = 10

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 400, 'E': 400, 'S': 400, 'W': 400}),
        ]

    @property
    def weapons(self):
        return {
            'L1': Laser('L1'),
            'L2': Laser('L2'),
            'M1': RocketLauncher('M1', Splinter(), 75),
            'M2': RocketLauncher('M2', Splinter(), 75)
        }
