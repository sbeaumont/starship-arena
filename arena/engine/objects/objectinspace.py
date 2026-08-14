"""
Abstract base class for all space objects.

It has support for:
- vector math (moving, position),
- the game engine's overridable hooks - which by default do nothing,
- storing the object's history - which is used for reporting, drawing, etc.
"""

import logging
from enum import Enum
from math import degrees, sqrt, atan2, pi
from abc import abstractmethod, ABC
from dataclasses import dataclass, replace

from arena.engine.history import History, Tick, TICK_ZERO
from arena.engine.objects.event import InternalEvent, Event
from arena.engine.objects.geometry import Leg, Point, Vector
from arena.engine.world import World

logger = logging.getLogger(__name__)


@dataclass
class Encounter:
    """Something within a range that matters, and how far into the tick it happens.

    Whatever answered with one is what acts when it is reached, so a caller never asks a second
    question to find out which kind of thing it was."""
    fraction: float

    @property
    def subject(self) -> 'ObjectInSpace':
        """Whatever it is that reaches something."""
        raise NotImplementedError

    def resolve(self, world: World):
        """Take the subject there, and then act. Nothing acts before it has arrived."""
        self.subject.move(self.fraction)
        self.act(world)

    def act(self, world: World):
        raise NotImplementedError


@dataclass
class Impulse:
    """A shove, as a change in momentum.

    Whoever produces one has worked out its strength already, so a receiver divides by its own
    mass and learns nothing about what hit it. A tick is the unit of time here, which is what
    makes an impulse and a force the same number."""
    source: 'ObjectInSpace'
    momentum: tuple

    @property
    def direction(self) -> float:
        """Which way the shove points."""
        mx, my = self.momentum
        return degrees(atan2(mx, my)) % 360

    @property
    def magnitude(self) -> float:
        """How hard it was."""
        mx, my = self.momentum
        return sqrt(mx * mx + my * my)


@dataclass
class Shove(Encounter):
    """Reaching something solid. Whatever arrives there takes the impulse it brings."""
    arriving: 'ObjectInSpace' = None
    impulse: Impulse = None

    @property
    def subject(self) -> 'ObjectInSpace':
        return self.arriving

    def act(self, world: World):
        self.arriving.take_impulse_from(self.impulse)


class Stance(str, Enum):
    """How one object in space stands towards another."""
    Friend = 'Friend'
    Foe = 'Foe'
    Neutral = 'Neutral'

    def __str__(self):
        return self.value


class ObjectInSpace(ABC):
    """Any object in space, which can be ships, rockets, starbases, black holes, etc."""
    def __init__(self, name: str, vector: Vector, tick: Tick = TICK_ZERO):
        assert isinstance(vector, Vector)
        super().__init__()
        self.name = name
        self.vector = vector
        self.moved_from = vector.pos
        self.owner = None
        self.faction = None
        self.history = History(self, tick)
        self.tags = set()
        # How much of the tick it has spent. Per-tick, like moved_from, and meaningless on its own.
        self.tick_fraction = 0.0

    # ---------------------------------------------------------------------- QUERIES

    @property
    def xy(self):
        """Raw position, not rounded"""
        return self.vector.pos

    @property
    def pos(self):
        return self.vector.pos.rounded(1)

    @property
    def heading(self):
        return round(self.vector.heading, 1)

    @property
    def speed(self):
        return round(self.vector.speed, 1)

    def distance_to(self, point: Point) -> float:
        assert isinstance(point, Point), f"{point} is not a Point"
        if isinstance(point, tuple):
            point = Point(*point)
        return round(sqrt((self.vector.x - point.x)**2 + (self.vector.y - point.y)**2), 1)

    @property
    def tick_ended(self) -> bool:
        """Nothing of this tick left to travel: it arrived, it is wedged, or it is dead."""
        return self.tick_fraction >= 1

    def position_at(self, fraction: float) -> Point:
        """Where it is at that fraction of the tick.

        With no tick left it is wherever it stopped, for the rest of it. Otherwise it is only ever
        asked about a fraction it has not passed, which is what the encounter loop guarantees:
        nothing advances while anything is pending at or before it."""
        if self.tick_ended:
            return self.vector.pos
        assert fraction >= self.tick_fraction, \
            f"{self.name} is at {self.tick_fraction}, past {fraction}"
        dx, dy = self.vector.delta
        ahead = fraction - self.tick_fraction
        return Point(self.vector.x + dx * ahead, self.vector.y + dy * ahead)

    def leg_from(self, fraction: float) -> Leg:
        """The travel still to come, from that fraction of the tick to the end of it."""
        dx, dy = self.vector.delta
        span = 1 - fraction
        return Leg(self.position_at(fraction), (dx * span, dy * span))

    @property
    def travelled(self) -> Leg:
        """The leg it is on. Only true once it has moved."""
        return Leg(self.moved_from, (self.vector.x - self.moved_from.x,
                                     self.vector.y - self.moved_from.y))

    def encounter(self, world: World) -> Encounter | None:
        """The first thing that comes within a range that matters, over the leg still to come.

        Anything solid stops it. A machine widens this with whatever its components answer."""
        if self.is_immovable or self.is_destroyed or self.tick_ended:
            return None
        found = None
        for other in [o for o in world.objects.values() if o.radius and o is not self]:
            from_fraction = max(self.tick_fraction, other.tick_fraction)
            span = 1 - from_fraction
            reached = self.leg_from(from_fraction).approach_fraction(
                other.leg_from(from_fraction), other.radius)
            if reached is None:
                continue
            at = from_fraction + reached * span
            # Name settles a dead heat, so which one the world lists first cannot decide it.
            if found is None or (at, other.name) < (found.fraction, found.impulse.source.name):
                impulse = other.impulse_on(self, at)
                if impulse:
                    found = Shove(at, self, impulse)
        return found

    def heading_to(self, point: Point) -> float:
        return round((atan2(point.x - self.vector.x, point.y - self.vector.y) / pi * 180) % 360, 1)

    def direction_to(self, point: Point) -> float:
        d = self.heading_to(point) - self.heading
        if d > 180:
            d -= 360
        elif d <= -180:
            d += 360
        return round(d, 1)

    @property
    def visibility(self) -> int:
        """How much of a scanner's reach this is worth to whoever is looking, as a percentage.

        The model's to answer: 100 is a standard object, a rock or a starbase is worth more, and
        anything hiding takes it down again through modify_scan_range."""
        return self._type.visibility

    def modify_scan_range(self, scan_range: float) -> float:
        """How far a scanner has to reach to find this."""
        return scan_range * (self.visibility / 100)

    @property
    def mass(self) -> float:
        """What there is of this to shift. A pickup or a powerup has none."""
        return 0

    @property
    def radius(self) -> float:
        """How much space this takes up, and so what stops at it. Most things are a point."""
        return 0

    @property
    def is_immovable(self) -> bool:
        """Effectively infinite mass, said without the arithmetic: the world moves around it."""
        return False

    @property
    def is_terrain(self) -> bool:
        """On every chart from the start, so nobody scans it. See docs/gddr/0038."""
        return False

    def stance_towards(self, other: 'ObjectInSpace') -> Stance:
        """Nothing in space is on a side until something puts it on one."""
        return Stance.Neutral

    @property
    @abstractmethod
    def type_name(self) -> str:
        """The name of this object's type, e.g. 'H2545', 'Rocket', 'SplinterMine'.

        Machines delegate to their type object; anything else added later - a black hole,
        an asteroid - names its own type.
        """
        ...

    @property
    @abstractmethod
    def category_name(self) -> str:
        """The kind of thing this is, e.g. 'Ship', 'Missile', 'Mine'.

        Where type_name is the model ('A2539'), this is the family it belongs to. Used to
        present objects meaningfully without having to recognise individual type names.
        """
        ...

    @property
    @abstractmethod
    def is_destroyed(self) -> bool:
        return False

    # ---------------------------------------------------------------------- HISTORY INTERFACE

    def add_event(self, event: Event):
        assert isinstance(event, Event)
        self.history.add_event(event)
        logger.debug(f"{self.name} event: {str(event)}")

    def add_internal_event(self, message: str):
        assert message is not None
        self.add_event(InternalEvent(message))

    def round_reset(self):
        self.history.reset()
        logger.debug(f"{self.name} round reset.")

    def post_round_reset(self):
        logger.debug(f"{self.name} post-round reset.")

    @property
    def snapshot(self):
        """This object's state for one tick. Each level adds what it owns; values, not references."""
        return {
            'name': self.name,
            'pos': self.pos,
            'xy': self.vector.pos,   # unrounded
            'heading': self.heading,
            'speed': self.speed,
            'owner': self.owner,
        }

    # ---------------------------------------------------------------------- COMMANDS

    def place_at(self, pos: Point):
        """Put this object somewhere without it having travelled there."""
        self.vector = replace(self.vector, pos=pos)
        self.moved_from = pos

    def face(self, point: Point):
        """Point this object at somewhere without it having turned."""
        self.vector = replace(self.vector, heading=self.heading_to(point))

    def end_tick(self):
        """Spend what is left of the tick where it stands, so a later move does nothing."""
        self.tick_fraction = 1

    def move(self, to_fraction: float = 1):
        """Advance along heading and speed to that fraction of the tick."""
        self.moved_from = self.vector.pos
        old_pos = self.moved_from.rounded().as_tuple
        self.vector = self.vector.move(to_fraction - self.tick_fraction)
        self.tick_fraction = to_fraction
        new_pos = self.vector.pos.rounded().as_tuple
        if old_pos != new_pos:
            logger.debug(f"{self.name} moving from {old_pos} to {new_pos} heading {self.heading}")
            self.add_internal_event(f"Moved from {old_pos} to {new_pos}")
        else:
            logger.debug(f"{self.name} no movement at {old_pos}")

    def accelerate(self, delta_v):
        self.vector = self.vector.accelerate(delta_v)

    @speed.setter
    def speed(self, amount):
        self.vector = replace(self.vector, speed=amount)

    # ---------------------------------------------------------------------- ENGINE HOOKS

    @property
    def is_player_controlled(self):
        return False

    def take_damage_from(self, hitevent):
        pass

    def tick(self, tick: Tick):
        self.tick_fraction = 0.0

    def generate(self):
        pass

    def use_energy(self):
        pass

    def scan(self, world: World):
        pass

    def take_impulse_from(self, impulse: Impulse):
        """A shove means nothing to most things."""
        pass

    def pre_move(self, world: World):
        pass

    def decide(self, world: World, tick: Tick):
        pass

    def post_move(self, world: World):
        pass