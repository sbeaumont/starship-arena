"""
Event class hierarchy for the event system.

Events get stored in the history of the relevant game objects to enable reporting.
"""


from dataclasses import dataclass, replace
from enum import Enum
from typing import Protocol, NewType

from arena.engine.objects.geometry import Circle, Line, Shape


class DamageType(Enum):
    """What kind of harm a HitEvent carries, which is what decides how a target answers it."""
    Explosion = 'Explosion'
    Nanocyte = 'Nanocyte'
    EMP = 'EMP'
    Impact = 'Impact'
    Laser = 'Laser'

    def __str__(self):
        return f"{self.value}"


class Outcome(Enum):
    """What a layer of a target did with the damage that reached it.

    Damage travels inwards: each defence component in turn, then the machine behind them. Every
    layer answers in the same three words, so armour or plating added later needs no new one.
    Damaged always means damaged and still there, because the alternative is Breached, and
    Breached on the machine itself is the end of it."""
    Unaffected = 'Unaffected'   # it went through this layer as if it were not there
    Damaged = 'Damaged'         # this layer took it and held
    Breached = 'Breached'       # this layer failed, and what was left carried on inwards

    def __str__(self):
        return f"{self.value}"


@dataclass
class Effect:
    """What one layer did with a blow that reached it. A component answers with one of these.

    `part` is the layer, as the symbol it calls itself: a component's name, or what of the machine
    took it. An interface turns these into words; nothing here does.

    What it never carries is the state the layer has left. A breach lets an attacker deduce a
    quadrant's strength from what carried on, and that is fair: they watched it fail. Handing over
    the remaining strength is not the same thing."""
    part: str
    outcome: Outcome
    amount: int        # what this layer took
    points: int        # what that was worth to whoever struck
    passed_on: int     # what was left over for the next layer inwards


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
    def __init__(self, location: EventLocation, event_type: str, source: EventSource):
        self.pos: EventLocation = location
        self._type: str = event_type
        self.source: EventSource = source
        self.effects: list[Effect] = []

    @property
    def can_score(self) -> bool:
        """Whether points off this can be claimed. Most events are worth nothing to anybody."""
        return False

    @property
    def shape(self) -> Shape | None:
        """What this covered beyond the point it happened at. Nothing, for most events."""
        return None

    @property
    def score(self) -> int:
        """What this was worth to whoever caused it.

        Totalled from the effects rather than counted up as it goes, so what the points were for
        survives beside how many there were."""
        return sum(e.points for e in self.effects)

    def add_effect(self, effect: Effect) -> None:
        """Take a layer's answer into the message. Whether it is worth anything is settled here,
        where the factions are known, so no component has to ask whose side it is on."""
        self.effects.append(effect if self.can_score else replace(effect, points=0))

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


class ReplenishEvent(InternalEvent):
    """A base restocking a ship. Read like a hit is: without turning every message on."""

    @property
    def kind(self) -> str:
        return 'replenish'


class ArrivalEvent(InternalEvent):
    """A ship reaching somewhere the game was played for. What that is worth is nobody's here."""

    def __init__(self, message, ship):
        super().__init__(message)
        self.ship = ship

    @property
    def kind(self) -> str:
        return 'arrival'


class ScanEvent(Event):
    """A single instance of one object scanning another."""
    def __init__(self, ois, distance, direction, heading):
        super().__init__(ois.pos, 'Scan', ois)
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
    def __init__(self, location, hit_type, source, target, amount: int, message: str = None):
        super().__init__(location, hit_type, source)
        self.target = target
        self.amount = int(round(amount, 0))
        self.message = message

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
        """The symbols read out as a sentence, until an interface takes that over."""
        if self.message:
            return self.message
        landed = f"{self.source.name} hit {self.target.name} with {self._type} for {self.amount}"
        if not self.effects:
            return landed
        return landed + ": " + ", ".join(
            f"{e.part} {e.outcome}" + (f" ({e.points} points)" if e.points else "")
            for e in self.effects)


class BeamEvent(HitEvent):
    """A hit that arrived along a line, where a blast arrives as a circle.

    A hit in every other way, and it reads as one: what it adds is that the two ends are worth
    drawing, and every hit already knows its source and its target."""

    # Loud, on the scale in GDDR 0031, though quieter than the blast that follows a warhead in.
    # A firefight is meant to be worth flying towards from a sector away.
    visibility = 500

    def __init__(self, location, hit_type, source, target, amount: int, fired_from,
                 message: str = None):
        super().__init__(location, hit_type, source, target, amount, message)
        self.fired_from = fired_from

    @property
    def shape(self) -> Shape:
        return Line(self.fired_from, self.pos)

    def modify_scan_range(self, scan_range: float) -> float:
        """How far a scanner has to reach to catch this going off, the way an object answers it."""
        return scan_range * (self.visibility / 100)


class ExplosionEvent(Event):
    # The loudest thing in the game, on the same scale an object's visibility uses. A blast
    # carries about a board width, so a fight anywhere tells everyone something is happening
    # without telling them what is in it.
    visibility = 1000

    def __init__(self, location, explosion_type, source, radius):
        super().__init__(location, explosion_type, source)
        self.radius = radius

    @property
    def shape(self) -> Shape:
        return Circle(self.pos, self.radius)

    def modify_scan_range(self, scan_range: float) -> float:
        """How far a scanner has to reach to see this go off, the way an object answers it."""
        return scan_range * (self.visibility / 100)

    @property
    def kind(self) -> str:
        return 'explosion'

    def __str__(self):
        return f"{self.source.name} exploded at {self.pos.as_tuple}"
