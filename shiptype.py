"""
Configurations of types of weapons and ships
"""

from weapon import Laser, RocketLauncher
from defense import Shields


class Splinter(object):
    max_speed = 60
    explode_distance = 6
    explode_damage = 10
    scan_distance = 150
    scan_cone = 45
    max_battery = 125
    hull = 1


class H2545(object):
    max_delta_v = 25
    max_speed = 45
    max_turn = 35
    generators = 8
    max_battery = 500
    start_battery = 125
    hull = 100

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 130, 'E': 100, 'S': 100, 'W': 100}),
        ]

    @property
    def weapons(self):
        return {
            'Laser1': Laser('Laser1'),
            'Launcher1': RocketLauncher('Launcher1', Splinter())
        }
