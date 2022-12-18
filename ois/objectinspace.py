import logging
from collections import namedtuple
from math import sin, cos, radians, sqrt, atan2, pi

logger = logging.getLogger(__name__)

Point = namedtuple("Point", "x y")


class Scan(object):
    """A single instance of one object scanning another."""
    def __init__(self, ois, distance, direction, heading):
        self.ois = ois
        self.name = ois.name
        self.pos = ois.pos
        self.distance = distance
        self.direction = direction
        self.heading = heading

    @classmethod
    def create_scan(cls, source, scanned):
        return cls(scanned,
                   round(source.distance_to(scanned.xy), 1),
                   round(source.direction_to(scanned.xy), 1),
                   round(source.heading_to(scanned.xy), 1))

    def __str__(self):
        return f"Scan({self.name}, {self.pos}, {self.distance}, {self.heading}, {self.direction})"


def translate(p: Point, heading, distance) -> Point:
    angle = radians(heading)
    new_x = p.x + (sin(angle) * distance)
    new_y = p.y + (cos(angle) * distance)
    return Point(new_x, new_y)


class ObjectInSpace(object):
    """Any object in space, which can be ships, rockets, starbases, black holes, etc."""
    def __init__(self, name: str, xy: tuple, heading: int = 0, speed: int = 0):
        super().__init__()
        assert isinstance(heading, int)
        self.name = name
        self.xy = Point(xy[0], xy[1])
        self.heading = heading
        self.speed = speed
        self.owner = None
        self.history = None

    # ---------------------------------------------------------------------- QUERIES

    @property
    def pos(self):
        return round(self.xy.x, 1), round(self.xy.y, 1)

    def distance_to(self, point: Point):
        return round(sqrt((self.xy.x - point.x)**2 + (self.xy.y - point.y)**2), 1)

    def heading_to(self, point: Point):
        return round((atan2(point.x - self.xy.x, point.y - self.xy.y) / pi * 180) % 360, 1)

    def direction_to(self, point: Point):
        return self.heading_to(point) - self.heading

    @property
    def is_destroyed(self) -> bool:
        return False

    # ---------------------------------------------------------------------- HISTORY INTERFACE

    def add_event(self, event):
        if self.history and event:
            self.history.add_event(event)

    def add_drawable_event(self, event_type, position, msg):
        self.history.add_drawable_event(event_type, position, msg)

    def round_reset(self):
        self.history.reset()

    # ---------------------------------------------------------------------- COMMANDS

    def move(self):
        """Move along heading with speed to next coordinate."""
        old_pos = self.pos
        self.xy = translate(self.xy, self.heading, self.speed)
        logger.debug(f"{self.name} moving from {old_pos} to {self.pos} heading {self.heading}")
        if old_pos != self.pos:
            self.add_event(f"Moved from {old_pos} to {self.pos}")

    def post_move(self, objects_in_space: dict):
        pass

    def generate(self):
        pass

    def scan(self, objects_in_space: dict):
        pass

    def take_damage_from(self, source_event, source_location, amount: int):
        pass


