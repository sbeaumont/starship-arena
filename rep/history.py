from abc import abstractmethod
from ois.objectinspace import Scan


class Snapshot(object):
    """Snapshot of an object in space, for attributes and for events."""
    def __init__(self):
        self.events = list()
        self.scans = list()

    @abstractmethod
    def update(self, obj):
        raise NotImplementedError()

    def add_event(self, event):
        self.events.append(event)
        return self

    def add_drawable_event(self, event_type, position, event):
        self.events.append(DrawableEvent(event_type, position, event))
        return self

    def add_scan(self, scan):
        self.scans.append(scan)

    @property
    def scan_events(self):
        return [e for e in self.events if e is Scan]

    @property
    def non_scan_events(self):
        return [e for e in self.events if e is not Scan]


class History(dict):
    """Holds snapshots and events per tick for its owner, to be used to report on the round."""
    def __init__(self, owner, snapshot_cls, tick: int):
        super().__init__()
        self.owner = owner
        self.snapshot_class = snapshot_cls
        self[tick] = self.create_snapshot()
        self.current = self[tick]

    def reset(self):
        self.clear()
        self[0] = self.create_snapshot()
        self.current = self[0]

    def add_event(self, event):
        assert event is not None
        self.current.add_event(event)

    def add_drawable_event(self, event_type, position, event):
        self.current.add_drawable_event(event_type, position, event)
        return self

    def update(self):
        self.current.update(self.owner)

    def create_snapshot(self):
        return self.snapshot_class()

    def set_tick(self, tick, update=True):
        if update:
            self.update()
        if tick not in self:
            self[tick] = self.create_snapshot()
        self.current = self[tick]


class DrawableEvent(object):
    """An event that should also be drawn on the round overview picture."""
    def __init__(self, event_type, position_or_line, msg):
        self.event_type = event_type
        self.position_or_line = position_or_line
        self.msg = msg

    def __str__(self):
        return self.msg


class ObjectInSpaceSnapshot(Snapshot):
    def update(self, obj):
        self.name = obj.name
        self.xy = obj.xy
        self.pos = obj.pos
        self.heading = obj.heading
        self.speed = obj.speed
        if hasattr(obj, 'scans'):
            self.scans = obj.scans
        return self


class RocketSnapshot(ObjectInSpaceSnapshot):
    def update(self, rocket):
        super().update(rocket)
        self.hull = rocket.hull
        self.battery = rocket.battery
        self.target = rocket.target
        return self


class ShipSnapshot(ObjectInSpaceSnapshot):
    def update(self, ship):
        super().update(ship)
        self.hull = ship.hull
        self.battery = ship.battery
        self.defense = ship.defense.copy()
        self.scans = ship.scans.copy()
        return self


class StarbaseSnapshot(ObjectInSpaceSnapshot):
    def update(self, starbase):
        super().update(starbase)
        self.hull = starbase.hull
        self.battery = starbase.battery
        self.defense = starbase.defense.copy()
        self.scans = starbase.scans.copy()
        return self

