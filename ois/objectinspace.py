import logging
from collections import namedtuple
from math import sin, cos, radians, sqrt, atan2, pi
from abc import abstractmethod, ABC

from ois.event import InternalEvent, Event
from rep.history import History

logger = logging.getLogger(__name__)

Point = namedtuple("Point", "x y")


def translate(p: Point, heading, distance) -> Point:
    angle = radians(heading)
    new_x = p.x + (sin(angle) * distance)
    new_y = p.y + (cos(angle) * distance)
    return Point(new_x, new_y)


class ObjectInSpace(ABC):
    """Any object in space, which can be ships, rockets, starbases, black holes, etc."""
    def __init__(self, name: str, xy: tuple, heading: int = 0, speed: int = 0, visibility: int = 100, tick: int = 0):
        super().__init__()
        self.name = name
        self.xy = Point(xy[0], xy[1])
        self.heading = heading
        self.speed = speed
        self.owner = None
        self.history = History(self, tick)
        self.visibility = visibility

    # ---------------------------------------------------------------------- QUERIES

    @property
    def pos(self):
        return round(self.xy.x, 1), round(self.xy.y, 1)

    def distance_to(self, point: Point):
        if isinstance(point, tuple):
            point = Point(*point)
        return round(sqrt((self.xy.x - point.x)**2 + (self.xy.y - point.y)**2), 1)

    def heading_to(self, point: Point):
        return round((atan2(point.x - self.xy.x, point.y - self.xy.y) / pi * 180) % 360, 1)

    def direction_to(self, point: Point):
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

    def round_reset(self):
        self.history.reset()

    @property
    def snapshot(self):
        return {
            'name': self.name,
            'xy': self.xy,
            'pos': self.pos,
            'heading': self.heading,
            'speed': self.speed,
            'owner': self.owner,
        }

    # ---------------------------------------------------------------------- COMMANDS

    def generate(self):
        pass

    def move(self):
        """Move along heading with speed to next coordinate."""
        old_pos = self.pos
        self.xy = translate(self.xy, self.heading, self.speed)
        logger.debug(f"{self.name} moving from {old_pos} to {self.pos} heading {self.heading}")
        if old_pos != self.pos:
            self.add_event(InternalEvent(f"Moved from {old_pos} to {self.pos}"))

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

