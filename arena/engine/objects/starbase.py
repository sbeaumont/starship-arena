"""
Starbase based on Ship:
- can not fly
- but carries what a fleet needs, a Replenisher among it.
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


class StarbaseType(ShipType):
    base_type = Starbase
    category = 'Starbase'

    # Big, bright and bolted down. A scanner reaches five times as far against one, so a base is
    # something everybody can find and nobody sneaks up on.
    visibility = 500
