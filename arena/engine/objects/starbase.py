"""
Starbase based on Ship:
- can not fly
- but can Replenish.
"""

import logging

from .ship import Ship

logger = logging.getLogger(__name__)


class Starbase(Ship):
    """Motionless space station that can still shoot, replenish and take a beating."""
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
            self.add_internal_event(f"Replenished {ship.name}")
            ship.add_internal_event(f"Replenished by {self.name}")
