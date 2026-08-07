"""
Event class hierarchy for the event system.

Events get stored in the history of the relevant game objects to enable reporting.
"""

from enum import Enum
from typing import Protocol, NewType


class DrawType(Enum):
    Point = 'Point'
    Circle = 'Circle'
    Line = 'Line'


class DamageType(Enum):
    """What kind of harm a HitEvent carries, which is what decides how a target answers it."""
    Explosion = 'Explosion'
    Nanocyte = 'Nanocyte'
    EMP = 'EMP'
    Impact = 'Impact'
    Laser = 'Laser'

    def __str__(self):
        return f"{self.value}"


class EventLocation(Protocol):
    x: float
    y: float


eventType = NewType('Event', object)


class EventSink(Protocol):
    name: str

    def add_event(self, event: eventType):
        ...


class EventSource(Protocol):
    name: str
    owner: EventSink

    def distance_to(self, p: EventLocation):
        ...

    def direction_to(self, p: EventLocation):
        ...

    def heading_to(self, p: EventLocation):
        ...


class Event(object):
    def __init__(self, location: EventLocation, event_type: str, source: EventSource, draw_type: DrawType=None):
        self.pos: EventLocation = location
        self._type: str = event_type
        self.source: EventSource = source
        self.draw_type: DrawType = draw_type

    def is_drawable(self):
        return self.draw_type is not None

    @property
    def kind(self) -> str:
        """What sort of event this is, for a UI to read.

        Each subclass answers for itself, the way ObjectInSpace.category_name does, so a reader
        never has to match on the wording of __str__ or know the Python class names."""
        raise NotImplementedError


class InternalEvent(Event):
    def __init__(self, message):
        super().__init__(None, 'Message', None)
        self.message = message

    @property
    def kind(self) -> str:
        return 'internal'

    def __str__(self):
        return self.message


class ScanEvent(Event):
    """A single instance of one object scanning another."""
    def __init__(self, ois, distance, direction, heading):
        super().__init__(ois.pos, 'Scan', ois, DrawType.Point)
        self.name = ois.name
        self.distance = distance
        self.direction = direction
        self.heading = heading

    @property
    def kind(self) -> str:
        return 'scan'

    @classmethod
    def create_scan(cls, source, scanned):
        return cls(scanned,
                   round(source.distance_to(scanned.xy), 1),
                   round(source.direction_to(scanned.xy), 1),
                   round(source.heading_to(scanned.xy), 1))

    def __str__(self):
        return f"Scanned {self.name} at {self.pos}, distance {self.distance}, direction {self.direction}, heading {self.heading}"


class HitEvent(Event):
    def __init__(self, location, hit_type, source, target, amount: int, draw_type: DrawType = None, message: str = None):
        super().__init__(location, hit_type, source, draw_type)
        self.target = target
        self.amount = int(round(amount, 0))
        self.message = message
        self.score = 0

    @property
    def kind(self) -> str:
        return 'hit'

    @property
    def can_score(self):
        """You don't score for hitting your own faction."""
        if self.target:
            return self.source.owner.faction != self.target.owner.faction
        else:
            return True

    def __str__(self):
        if self.message:
            return self.message
        else:
            return f"{self.source.name} hit {self.target.name} with {self._type} for {self.amount}"

    def notify_owner(self, message: str):
        self.source.owner.add_event(InternalEvent(message))


class ExplosionEvent(Event):
    def __init__(self, location, explosion_type, source, radius):
        super().__init__(location, explosion_type, source, DrawType.Circle)
        self.radius = radius

    @property
    def kind(self) -> str:
        return 'explosion'

    def __str__(self):
        return f"{self.source.name} exploded at {self.pos.as_tuple}"
