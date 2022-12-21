from enum import Enum


class DrawType(Enum):
    Point = 'Point'
    Circle = 'Circle'
    Line = 'Line'


class Event(object):
    def __init__(self, location, event_type, source, draw_type: DrawType=None):
        self.pos = location
        self._type = event_type
        self.source = source
        self.draw_type = draw_type

    def is_drawable(self):
        return self.draw_type is not None


class InternalEvent(Event):
    def __init__(self, message):
        super().__init__(None, 'Message', None)
        self.message = message

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

    @classmethod
    def create_scan(cls, source, scanned):
        return cls(scanned,
                   round(source.distance_to(scanned.xy), 1),
                   round(source.direction_to(scanned.xy), 1),
                   round(source.heading_to(scanned.xy), 1))

    def __str__(self):
        return f"Scanned {self.name} at {self.pos}, distance {self.distance}, direction {self.direction}, heading {self.heading}"


class HitEvent(Event):
    def __init__(self, location, hit_type, source, target, amount, draw_type: DrawType=None, message: str=None):
        super().__init__(location, hit_type, source, draw_type)
        self.target = target
        self.amount = amount
        self.message = message
        self.score = 0

    def __str__(self):
        if self.message:
            return self.message
        else:
            return f"{self.source.name} hit {self.target.name} with {self._type} for {self.amount}"


class ExplosionEvent(Event):
    def __init__(self, location, explosion_type, source, radius):
        super().__init__(location, explosion_type, source, DrawType.Circle)
        self.radius = radius

    def __str__(self):
        return f"{self.source.name} exploded at {self.pos}"
