import logging

from comp.defense import Shields
from comp.weapon import Laser, RocketLauncher
from ois.ship import Ship
from ois.rocket import Splinter
from rep.history import StarbaseSnapshot

logger = logging.getLogger(__name__)


class Starbase(Ship):
    def turn(self, angle):
        """Starbases don't turn. Nice try."""
        pass

    def accelerate(self, delta_v):
        """Starbases don't accelerate. Nice try."""
        pass

    def move(self):
        """Starbases do not move."""
        pass

    def replenish(self, ship: Ship):
        if (self.distance_to(ship.xy) <= self._type.max_replenish_distance) and \
                (ship.speed <= self._type.max_replenish_speed):
            ship.hull = ship._type.max_hull
            ship.battery = ship._type.max_battery
            for weapon in ship.weapons.values():
                weapon.reset()
            self.add_event(f"Replenished {ship.name}")
            ship.add_event(f"Replenished by {self.name}")


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
    max_hull = 250
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