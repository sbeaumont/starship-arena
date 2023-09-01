from ois.event import ScanEvent, HitEvent
from collections import defaultdict


class TickHistory(object):
    __slots__ = ('data', 'events', 'score')
    """Snapshot of an object in space, for attributes and for events."""
    def __init__(self):
        self.data = dict()
        self.events = list()
        self.score = 0

    # ---------------------------------------------------------------------- QUERIES

    def __getitem__(self, item):
        return self.data[item]

    def __contains__(self, item):
        return self.data.__contains__(item)

    def __iter__(self):
        return self.data.__iter__()

    def keys(self):
        return self.data.keys()

    @property
    def scans(self):
        return [e for e in self.events if isinstance(e, ScanEvent)]

    @property
    def hits(self):
        return [e for e in self.events if isinstance(e, HitEvent)]

    @property
    def hit_score(self):
        return sum([e.score for e in self.hits if e.can_score])

    def scan_by_name(self, name):
        named_scans = [s for s in self.scans if s.name == name]
        if len(named_scans) >= 1:
            assert len(named_scans) == 1, f"Hey weird, got more than one scan for a name in a tick: {[str(s) for s in self.scans]}"
            return named_scans[0]
        return None

    @property
    def non_scan_events(self):
        return [e for e in self.events if not isinstance(e, ScanEvent)]

    # ---------------------------------------------------------------------- COMMANDS

    def update(self, snapshot: dict):
        self.data.update(snapshot)

    def add_event(self, event):
        if event not in self.events:
            self.events.append(event)
        return self


class History(object):
    __slots__ = ('owner', 'ticks', 'current')
    """Holds snapshots and events per tick for its owner, to be used to report on the round."""
    def __init__(self, owner, tick: int):
        super().__init__()
        self.owner = owner
        self.ticks = defaultdict(TickHistory)
        self.current: TickHistory = self.ticks[tick]

    # ---------------------------------------------------------------------- QUERIES

    def __getitem__(self, item):
        return self.ticks[item]

    def __contains__(self, item):
        return self.ticks.__contains__(item)

    def __iter__(self):
        return self.ticks.__iter__()

    def keys(self):
        return self.ticks.keys()

    # ---------------------------------------------------------------------- COMMANDS

    def add_event(self, event):
        assert event is not None
        # Bit of a hack to ensure we don't score an event twice for scoring...
        if event not in self.current.events:
            # Make sure the event first processed "take damage from" to ensure it has a score.
            if isinstance(event, HitEvent) and (event.source.owner == self.owner):
                self.current.score += event.score
                self.owner.score += event.score
            self.current.add_event(event)

    def create_snapshot(self):
        return self.owner.snapshot

    def reset(self):
        self.ticks.clear()
        self.ticks[0].update(self.create_snapshot())
        self.current = self.ticks[0]

    def set_tick(self, tick, update=True):
        if update:
            self.update()
        self.current = self.ticks[tick]

    def update(self):
        self.current.update(self.owner.snapshot)

    @property
    def events_per_tick(self):
        result = defaultdict(list)
        for tick, th in self.ticks.items():
            result[tick] = th.non_scan_events
        return result

    @property
    def scans_per_tick(self):
        result = defaultdict(list)
        for tick, th in self.ticks.items():
            result[tick] = th.scans
        return result

    @property
    def hit_scores_per_tick(self):
        result = defaultdict(list)
        for tick, th in self.ticks.items():
            result[tick] = th.hit_score
        return result
