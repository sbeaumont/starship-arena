"""
Starbase based on Ship:
- can not fly
- but can Replenish.
"""

import logging

from .ship import Ship, ShipType

logger = logging.getLogger(__name__)


class Starbase(Ship):
    """Motionless space station that can still shoot, replenish and take a beating."""

    @property
    def category_name(self) -> str:
        return 'Starbase'

    @property
    def is_immovable(self) -> bool:
        """Bolted down, the way a planet is."""
        return True

    def turn(self, angle):
        """Starbases don't turn. Nice try."""
        pass

    def accelerate(self, delta_v):
        """Starbases don't accelerate. Nice try."""
        pass

    def move(self, fraction: float = 1, impulse=None):
        """Starbases do not move."""
        pass

    def replenish(self, ship: Ship):
        if (self.distance_to(ship.xy) <= self._type.max_replenish_distance) and \
                (ship.speed <= self._type.max_replenish_speed):
            ship.hull = ship._type.max_hull
            ship.battery = ship._type.max_battery
            for component in ship.all_components.values():
                component.reset()
            self.add_internal_event(f"Replenished {ship.name}")
            ship.add_internal_event(f"Replenished by {self.name}")


class StarbaseType(ShipType):
    base_type = Starbase
    category = 'Starbase'

    # Big, bright and bolted down. A scanner reaches five times as far against one, so a base is
    # something everybody can find and nobody sneaks up on.
    visibility = 500

    max_replenish_distance = None
    max_replenish_speed = None
