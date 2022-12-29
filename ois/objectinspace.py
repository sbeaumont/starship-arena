import logging
from math import sin, cos, radians, sqrt, atan2, pi
from abc import abstractmethod, ABC
from dataclasses import dataclass, replace

from .event import InternalEvent, Event
from rep.history import History

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
    def __init__(self, name: str, vector: Vector, visibility: int = 100, tick: int = 0):
        assert isinstance(vector, Vector)
        super().__init__()
        self.name = name
        self.vector = vector
        self.owner = None
        self.history = History(self, tick)
        self.visibility = visibility

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

    def heading_to(self, point: Point) -> float:
        return round((atan2(point.x - self.vector.x, point.y - self.vector.y) / pi * 180) % 360, 1)

    def direction_to(self, point: Point) -> float:
        return self.heading_to(point) - self.heading

    def modify_scan_range(self, scan_range: float) -> float:
        """Change a scanning object's scan range based on this object's visibility."""
        return scan_range * (self.visibility / 100)

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

    @property
    def snapshot(self):
        return {
            'name': self.name,
            'xy': self.vector.pos,
            'pos': self.pos,
            'heading': self.heading,
            'speed': self.speed,
            'owner': self.owner,
        }

    # ---------------------------------------------------------------------- COMMANDS

    def move(self):
        """Move along heading with speed to next coordinate."""
        old_pos = self.vector.pos.rounded().as_tuple
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

    def take_damage_from(self, hitevent):
        pass

    # ---------------------------------------------------------------------- ENGINE HOOKS

    def tick(self, tick_nr):
        pass

    def generate(self):
        pass

    def use_energy(self):
        pass

    def scan(self, objects_in_space: dict):
        pass

    def pre_move(self, objects_in_space: dict):
        pass

    def post_move(self, objects_in_space: dict):
        pass
