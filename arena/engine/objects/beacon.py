"""Somewhere to get to. Between terrain and a machine: it cannot be destroyed and it notices.

Solid, so it is docked with rather than flown through, and small enough that reaching it is a
piece of navigation. What arriving is worth is the scenario's, never this file's.
"""

from arena.engine.history import Tick, TICK_ZERO
from arena.engine.objects.event import ArrivalEvent
from arena.engine.objects.geometry import Vector
from arena.engine.objects.objectinspace import Impulse, ObjectInSpace
from arena.engine.world import World


class BeaconType(object):
    """Type Object for a Beacon, the way BodyType is for terrain."""
    base_type = None
    radius = 0

    # How near, and how slowly, a ship has to be to have arrived. The same shape a starbase's
    # Replenisher uses: coming alongside is the manoeuvre, not crossing a line at speed.
    dock_range = 0
    max_approach_speed = 0

    visibility = 100

    # It observes nothing, so it is never the one that saw an explosion. Warhead.explode asks
    # every object's type this.
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


class Beacon(ObjectInSpace):
    """A fixed mark that records who has docked with it."""

    def __init__(self, name: str, _type: BeaconType, vector: Vector, owner=None,
                 tick: Tick = TICK_ZERO):
        assert isinstance(_type, BeaconType), f"{_type} is not an instance of BeaconType"
        super().__init__(name, vector, tick=tick)
        self._type = _type
        self.owner = self
        # Who has been here. Arriving is the thing that happened; staying alongside is not, and
        # this is also what anything asking whether the game is over reads.
        self.docked = set()

    # ---------------------------------------------------------------------- QUERIES

    @property
    def type_name(self) -> str:
        return self._type.type_name

    @property
    def category_name(self) -> str:
        return 'Beacon'

    @property
    def is_destroyed(self) -> bool:
        return False

    @property
    def is_immovable(self) -> bool:
        return True

    @property
    def radius(self) -> float:
        return self._type.radius

    def has_docked(self, ois: ObjectInSpace) -> bool:
        return (self.distance_to(ois.xy) <= self._type.dock_range
                and abs(ois.speed) <= self._type.max_approach_speed)

    def impulse_on(self, other: ObjectInSpace, fraction: float) -> Impulse | None:
        """Nothing bounces off it: a mark you have to dock with may not shove you away first."""
        return None

    # ---------------------------------------------------------------------- HISTORY INTERFACE

    @property
    def snapshot(self):
        snap = super().snapshot
        snap['radius'] = self.radius
        return snap

    # ---------------------------------------------------------------------- ENGINE HOOKS

    def move(self, fraction: float = 1, impulse=None):
        pass

    def post_move(self, world: World):
        """Everything has moved by now, so who is alongside is a fact rather than a race."""
        for ois in world.objects.values():
            if ois is self or ois.name in self.docked or not self.has_docked(ois):
                continue
            self.docked.add(ois.name)
            arrival = ArrivalEvent(f"{ois.name} docked at {self.name}.", ois)
            self.add_event(arrival)
            ois.add_event(arrival)