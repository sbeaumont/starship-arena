import logging
from math import sin, cos, radians, sqrt, atan2, pi
from abc import abstractmethod, ABC
from dataclasses import dataclass

from ois.event import InternalEvent, Event
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
    angle: float
    length: float

    @property
    def x(self):
        return self.pos.x

    @property
    def y(self):
        return self.pos.y

    def rounded(self, digits=1):
        return Vector(
            pos=self.pos.rounded(digits),
            angle=round(self.angle, digits),
            length=round(self.length, digits)
        )

    def translate(self, direction, distance):
        return Vector(self.pos.translate(direction, distance), self.angle, self.length)

    def move(self):
        return self.translate(self.angle, self.length)

    def turn(self, angle):
        return Vector(self.pos, self.angle + angle, self.length)

    def accelerate(self, delta_v):
        return Vector(self.pos, self.angle, self.length + delta_v)


class ObjectInSpace(ABC):
    """Any object in space, which can be ships, rockets, starbases, black holes, etc."""
    def __init__(self, name: str, xy: Point, heading: int = 0, speed: int = 0, visibility: int = 100, tick: int = 0):
        assert isinstance(xy, Point)
        super().__init__()
        self.name = name
        self.vector = Vector(xy, angle=heading, length=speed)
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
        return round(self.vector.angle, 1)

    @property
    def speed(self):
        return round(self.vector.length, 1)

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

    def add_internal_event(self, message: str):
        assert message is not None
        self.history.add_event(InternalEvent(message))

    def round_reset(self):
        self.history.reset()

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
        old_pos = self.vector.pos
        self.vector = self.vector.move()
        logger.debug(f"{self.name} moving from {old_pos} to {self.vector.pos} heading {self.heading}")
        if old_pos != self.pos:
            self.add_event(InternalEvent(f"Moved from {old_pos} to {self.pos}"))

    def accelerate(self, delta_v):
        self.vector = self.vector.accelerate(delta_v)

    @speed.setter
    def speed(self, amount):
        self.vector.length = amount

    def generate(self):
        pass

    def scan(self, objects_in_space: dict):
        pass

    def take_damage_from(self, hitevent):
        pass

    # ---------------------------------------------------------------------- ENGINE HOOKS

    def tick(self, tick_nr):
        pass

    def use_energy(self):
        pass

    def pre_move(self, objects_in_space: dict):
        pass

    def post_move(self, objects_in_space: dict):
        pass

