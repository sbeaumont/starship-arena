from ois.event import ScanEvent
from collections import defaultdict


class TickHistory(object):
    __slots__ = ('data', 'events')
    """Snapshot of an object in space, for attributes and for events."""
    def __init__(self):
        self.data = dict()
        self.events = set()

    def __getitem__(self, item):
        return self.data[item]

    def __contains__(self, item):
        return self.data.__contains__(item)

    def __iter__(self):
        return self.data.__iter__()

    def keys(self):
        return self.data.keys()

    def update(self, snapshot: dict):
        self.data.update(snapshot)

    def add_event(self, event):
        self.events.add(event)
        return self

    @property
    def scans(self):
        return [e for e in self.events if isinstance(e, ScanEvent)]

    def scan_by_name(self, name):
        named_scans = [s for s in self.scans if s.name == name]
        if len(named_scans) >= 1:
            assert len(named_scans) == 1, f"Hey weird, got more than one scan for a name in a tick: {self.scans}"
            return named_scans[0]
        return None

    @property
    def non_scan_events(self):
        return [e for e in self.events if not isinstance(e, ScanEvent)]


class History(object):
    __slots__ = ('owner', 'ticks', '_current')
    """Holds snapshots and events per tick for its owner, to be used to report on the round."""
    def __init__(self, owner, tick: int):
        super().__init__()
        self.owner = owner
        self.ticks = defaultdict(TickHistory)
        self._current: TickHistory = self.ticks[tick]
        self.update()

    def __getitem__(self, item):
        return self.ticks[item]

    def __contains__(self, item):
        return self.ticks.__contains__(item)

    def __iter__(self):
        return self.ticks.__iter__()

    def keys(self):
        return self.ticks.keys()

    def reset(self):
        self.ticks.clear()
        self.ticks[0].update(self.create_snapshot())
        self._current = self.ticks[0]

    def add_event(self, event):
        assert event is not None
        self._current.add_event(event)

    def update(self):
        self._current.update(self.owner.snapshot)

    def create_snapshot(self):
        return self.owner.snapshot

    def set_tick(self, tick, update=True):
        if update:
            self.update()
        self._current = self.ticks[tick]
