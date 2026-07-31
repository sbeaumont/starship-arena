"""
Abstract base class for all space objects.

It has support for:
- vector math (moving, position),
- the game engine's overridable hooks - which by default do nothing,
- storing the object's history - which is used for reporting, drawing, etc.
"""

import logging
from math import sin, cos, radians, sqrt, atan2, pi
from abc import abstractmethod, ABC
from dataclasses import dataclass, replace

from .event import InternalEvent, Event
from arena.engine.history import History, Tick, TICK_ZERO
from arena.engine.world import World

logger = logging.getLogger(__name__)


@dataclass
class Point(object):
    x: float
    y: float

    def translate(self, direction, distance):
        angle = radians(direction)
        new_x = self.x + (sin(angle) * distance)
        new_y = self.y + (cos(angle) * distance)
        return Point(new_x, new_y)

    def move(self, xy: tuple):
        return Point(self.x + xy[0], self.y + xy[1])

    def rounded(self, digits=1):
        return Point(x=round(self.x, digits), y=round(self.y, digits))

    @property
    def as_tuple(self):
        return self.x, self.y


@dataclass
class Vector(object):
    pos: Point
    heading: float
    speed: float

    def __post_init__(self):
        # A heading is a direction, so 450 and 90 are the same one. direction_to folds a
        # difference into [-180, 180] with a single wrap, and gets it wrong for anything
        # further out, so a heading never gets to leave the circle.
        self.heading = self.heading % 360

    @property
    def x(self):
        return self.pos.x

    @property
    def y(self):
        return self.pos.y

    def rounded(self, digits=1):
        return Vector(
            pos=self.pos.rounded(digits),
            heading=round(self.heading, digits),
            speed=round(self.speed, digits)
        )

    def translate(self, direction, distance):
        return replace(self, pos=self.pos.translate(direction, distance))

    def move(self):
        return self.translate(self.heading, self.speed)

    def turn(self, angle):
        return replace(self, heading=self.heading + angle)

    def accelerate(self, delta_v):
        return replace(self, speed=self.speed + delta_v)

    def copy(self):
        return replace(self)


class ObjectInSpace(ABC):
    """Any object in space, which can be ships, rockets, starbases, black holes, etc."""
    def __init__(self, name: str, vector: Vector, visibility: int = 100, tick: Tick = TICK_ZERO):
        assert isinstance(vector, Vector)
        super().__init__()
        self.name = name
        self.vector = vector
        self.moved_from = vector.pos
        self.owner = None
        self.faction = None
        self.history = History(self, tick)
        self.visibility = visibility
        self.tags = set()

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

    def position_at(self, fraction: float) -> Point:
        """Where this object was, that far through the travel it made this tick."""
        return Point(
            self.moved_from.x + (self.vector.x - self.moved_from.x) * fraction,
            self.moved_from.y + (self.vector.y - self.moved_from.y) * fraction,
        )

    def approach_fraction(self, other: 'ObjectInSpace', distance: float) -> float | None:
        """How far into this tick the gap to other first closed to distance, None if it never did.

        A tick is a jump: move() translates the whole speed at once, so comparing only where the
        two ended up lets a rocket flying 60 a tick pass clean through the ship it was aimed at.
        Both objects travelled, so the test is on the gap between the two paths.
        """
        gap_x = self.moved_from.x - other.moved_from.x
        gap_y = self.moved_from.y - other.moved_from.y
        outside = gap_x * gap_x + gap_y * gap_y - distance * distance
        if outside <= 0:
            return 0.0

        closing_x = (self.vector.x - self.moved_from.x) - (other.vector.x - other.moved_from.x)
        closing_y = (self.vector.y - self.moved_from.y) - (other.vector.y - other.moved_from.y)
        closing = closing_x * closing_x + closing_y * closing_y
        if closing == 0:
            return None

        along = 2 * (gap_x * closing_x + gap_y * closing_y)
        discriminant = along * along - 4 * closing * outside
        if discriminant < 0:
            return None

        fraction = (-along - sqrt(discriminant)) / (2 * closing)
        return fraction if 0 <= fraction <= 1 else None

    def heading_to(self, point: Point) -> float:
        return round((atan2(point.x - self.vector.x, point.y - self.vector.y) / pi * 180) % 360, 1)

    def direction_to(self, point: Point) -> float:
        d = self.heading_to(point) - self.heading
        if d > 180:
            d -= 360
        elif d <= -180:
            d += 360
        return round(d, 1)

    def modify_scan_range(self, scan_range: float) -> float:
        """Change a scanning object's scan range based on this object's visibility."""
        return scan_range * (self.visibility / 100)

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

    def move(self):
        """Move along heading with speed to next coordinate."""
        self.moved_from = self.vector.pos
        old_pos = self.moved_from.rounded().as_tuple
        self.vector = self.vector.move()
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
        pass

    def generate(self):
        pass

    def use_energy(self):
        pass

    def scan(self, world: World):
        pass

    def pre_move(self, world: World):
        pass

    def decide(self, world: World, tick: Tick):
        pass

    def post_move(self, world: World):
        pass
