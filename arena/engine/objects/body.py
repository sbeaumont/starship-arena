"""Terrain: something big enough to run into, and too big to be moved by it.

A body is not a machine. It has no hull, no battery and no components, so it answers the engine's
hooks with the defaults and does nothing all round. What it has is a radius, which is what makes
anything stop at it. See docs/adr/0023-a-tick-advances-by-encounters.md.
"""

from math import cos, radians, sin

from .objectinspace import Impulse, ObjectInSpace, Vector
from arena.engine.history import Tick, TICK_ZERO

# How much of the arrival a body gives back. Nothing below a crawl, so a mine that drifts into
# one settles against it rather than bouncing for ever at a smaller amplitude every time.
RESTITUTION = 0.3
SETTLE_SPEED = 5


class BodyType(object):
    """Type Object for a Body, the way MachineType is for a machine."""
    base_type = None
    radius = 0

    # The other end of a cloak: a scanner reaches this much further against something this big,
    # so a rock is picked up long before a ship of the same size would be. Nobody is ambushed by
    # terrain.
    visibility = 300

    # Terrain observes nothing, so it is never the one that saw an explosion. Warhead.explode
    # asks every object's type this, which is why a body has to have an answer.
    max_scan_distance = 0

    def create(self, name: str, vector: Vector, owner=None, tick: Tick = TICK_ZERO):
        assert self.base_type, f"{self.name} does not have a base_type defined"
        return self.base_type(name, self, vector, owner=owner, tick=tick)

    @property
    def type_name(self) -> str:
        return self.__class__.__name__

    @property
    def name(self) -> str:
        return self.type_name


class Body(ObjectInSpace):
    """A lump of rock in space. Impassable, indestructible, and it never moves."""

    def __init__(self, name: str, _type: BodyType, vector: Vector, owner=None, tick: Tick = TICK_ZERO):
        assert isinstance(_type, BodyType), f"{_type} is not an instance of BodyType"
        super().__init__(name, vector, tick=tick)
        self._type = _type
        # Its own owner, the way a ship is, because plenty of code asks an object's owner for a
        # faction and a body has nobody above it to ask.
        self.owner = self

    # ---------------------------------------------------------------------- QUERIES

    @property
    def type_name(self) -> str:
        return self._type.type_name

    @property
    def category_name(self) -> str:
        return 'Terrain'

    @property
    def is_destroyed(self) -> bool:
        return False

    @property
    def is_immovable(self) -> bool:
        return True

    @property
    def radius(self) -> float:
        return self._type.radius

    def impulse_on(self, other: ObjectInSpace, fraction: float) -> Impulse | None:
        """The shove something gets for arriving here, or nothing if it was already leaving.

        Only what runs into the surface is turned around. What runs along it keeps going, which
        is why a graze costs almost nothing and a square hit costs everything."""
        normal = self.heading_to(other.position_at(fraction))
        closing = -other.vector.component_along(normal)
        if closing <= 0:
            return None
        strength = other.mass * (1 + (RESTITUTION if closing >= SETTLE_SPEED else 0)) * closing
        angle = radians(normal)
        return Impulse(self, (strength * sin(angle), strength * cos(angle)))

    # ---------------------------------------------------------------------- HISTORY INTERFACE

    @property
    def snapshot(self):
        snap = super().snapshot
        snap['radius'] = self.radius
        return snap

    # ---------------------------------------------------------------------- ENGINE HOOKS

    def move(self, fraction: float = 1, impulse=None):
        """Terrain stays where it is."""
        pass