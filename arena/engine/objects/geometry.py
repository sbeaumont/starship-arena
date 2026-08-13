"""Geometry: where things are, how they travel, and what shape they manifest as.

Values, all of them. Nothing here knows what an object in space is.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from math import sin, cos, radians, degrees, sqrt, atan2, copysign

# A gap of nothing has no direction, so a closest fraction stops this far short of one. A tenth
# is what survives Point.rounded; anything smaller reads as a direct hit again.
MIN_GAP = 0.1


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

    @property
    def delta(self) -> tuple:
        """This tick's travel, as a change in x and y."""
        angle = radians(self.heading)
        return sin(angle) * self.speed, cos(angle) * self.speed

    def with_delta(self, dx: float, dy: float) -> 'Vector':
        """The same position, travelling as that change in x and y describes.

        Keeps the sense it had, so something that was reversing goes on reversing and faces the way
        it faced rather than the way it now travels."""
        travel = degrees(atan2(dx, dy)) % 360
        astern = self.speed < 0
        return replace(self,
                       heading=(travel + 180) % 360 if astern else travel,
                       speed=copysign(sqrt(dx * dx + dy * dy), self.speed))

    def component_along(self, direction: float) -> float:
        """How much of this travel runs in that direction, negative when it runs against it."""
        angle = radians(direction)
        dx, dy = self.delta
        return dx * sin(angle) + dy * cos(angle)

    def translate(self, direction, distance):
        return replace(self, pos=self.pos.translate(direction, distance))

    def move(self, fraction: float = 1):
        return self.translate(self.heading, self.speed * fraction)

    def turn(self, angle):
        return replace(self, heading=self.heading + angle)

    def accelerate(self, delta_v):
        return replace(self, speed=self.speed + delta_v)

    def copy(self):
        return replace(self)


@dataclass
class Leg:
    """One tick's travel: where it starts, and how far it goes in x and y.

    A tick is a jump, so a rocket doing 60 has a leg rather than a position, and every question
    about what it passed is a question about the leg."""
    start: Point
    delta: tuple

    def _closing_on(self, other: 'Leg') -> tuple:
        """The gap this leg starts with, and how that gap changes over the tick."""
        return ((self.start.x - other.start.x, self.start.y - other.start.y),
                (self.delta[0] - other.delta[0], self.delta[1] - other.delta[1]))

    def closest_fraction(self, other: 'Leg', max_distance: float) -> float | None:
        """Where the gap between the two legs is shortest, None if it stays beyond max_distance.

        Both travelled, so the gap is between the legs, and it is shortest where the relative
        movement runs square to it."""
        (gap_x, gap_y), (closing_x, closing_y) = self._closing_on(other)
        closing = closing_x * closing_x + closing_y * closing_y
        if closing == 0:
            return 0.0 if (gap_x * gap_x + gap_y * gap_y) <= max_distance * max_distance else None

        # Square to the gap can fall outside the leg, and then the nearer end of it is the answer.
        fraction = min(max(-(gap_x * closing_x + gap_y * closing_y) / closing, 0.0), 1.0)
        shortest_x = gap_x + fraction * closing_x
        shortest_y = gap_y + fraction * closing_y
        shortest = shortest_x * shortest_x + shortest_y * shortest_y
        if shortest > max_distance * max_distance:
            return None
        if shortest < MIN_GAP * MIN_GAP:
            fraction -= sqrt(MIN_GAP * MIN_GAP - shortest) / sqrt(closing)
        return max(fraction, 0.0)

    def approach_fraction(self, other: 'Leg', max_distance: float) -> float | None:
        """Where the gap between the two legs first closes to max_distance, None if it never does.

        Where something stops that may come no nearer, such as the surface of a solid body."""
        (gap_x, gap_y), (closing_x, closing_y) = self._closing_on(other)
        outside = gap_x * gap_x + gap_y * gap_y - max_distance * max_distance
        if outside <= 0:
            return 0.0

        closing = closing_x * closing_x + closing_y * closing_y
        if closing == 0:
            return None

        along = 2 * (gap_x * closing_x + gap_y * closing_y)
        discriminant = along * along - 4 * closing * outside
        if discriminant < 0:
            return None

        fraction = (-along - sqrt(discriminant)) / (2 * closing)
        return fraction if 0 <= fraction <= 1 else None


class Shape(ABC):
    """What something manifests as in the world. Whole on its own, and it names itself."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Which shape this is."""

    @property
    @abstractmethod
    def measurements(self) -> dict[str, float]:
        """Where it is and how big, flat, by name."""


@dataclass(frozen=True)
class Circle(Shape):
    """It covers this far in every direction from its centre."""
    centre: Point
    radius: float

    @property
    def name(self) -> str:
        return 'circle'

    @property
    def measurements(self) -> dict[str, float]:
        return {'x': self.centre.x, 'y': self.centre.y, 'radius': self.radius}


@dataclass(frozen=True)
class Line(Shape):
    """It runs between its two ends."""
    p1: Point
    p2: Point

    @property
    def name(self) -> str:
        return 'line'

    @property
    def measurements(self) -> dict[str, float]:
        return {'x1': self.p1.x, 'y1': self.p1.y, 'x2': self.p2.x, 'y2': self.p2.y}