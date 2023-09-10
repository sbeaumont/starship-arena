from ois.event import ScanEvent, HitEvent
from collections import defaultdict
from dataclasses import dataclass, field, astuple


@dataclass(order=True, frozen=True, eq=True)
class Tick(object):
    round: int = field(compare=False)
    tick: int = field(compare=False)
    abs_tick: int = field(init=False, compare=True)

    def __post_init__(self):
        object.__setattr__(self, 'abs_tick', (self.round * 10) + self.tick)
        if self.abs_tick % 10 == 0 and self.tick == 0:
            object.__setattr__(self, 'round', self.round - 1)
            object.__setattr__(self, 'tick', 10)

    @classmethod
    def from_abs(cls, abs_tick: int):
        return Tick(abs_tick // 10, abs_tick % 10)

    @classmethod
    def for_start_of_round(cls, round_nr: int):
        return Tick(round_nr, 1)

    @property
    def next(self):
        return Tick.from_abs(self.abs_tick + 1)

    @property
    def prev(self):
        return Tick.from_abs(self.abs_tick - 1)

    @property
    def round_start(self):
        return Tick.for_start_of_round(self.round)

    @property
    def round_end(self):
        return Tick(self.round, 10)

    @property
    def ticks_for_round(self) -> list:
        range_start = self.round_start.abs_tick
        range_end = self.round_end.abs_tick + 1
        return [Tick.from_abs(t) for t in range(range_start, range_end)]

    @property
    def prev_round_end(self):
        return Tick(self.round - 1, 10)

    def __hash__(self):
        return self.abs_tick


TICK_ZERO = Tick(0, 10)


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
            assert len(named_scans) == 1, f"More than one scan for one name in TickHistory: {[str(s) for s in self.scans]}"
            return named_scans[0]
        return None

    @property
    def non_scan_events(self):
        return [e for e in self.events if not isinstance(e, ScanEvent)]

    # ---------------------------------------------------------------------- COMMANDS

    def update(self, snapshot: dict):
        self.data.update(snapshot)

    def add_event(self, event):
        if isinstance(event, ScanEvent):
            scanned_names = [s.name for s in self.scans]
            if event.name in scanned_names:
                return self
            # assert event.name not in scanned_names, f"Trying to add scan for {event} while name already is present in {scanned_names}."
        if event not in self.events:
            self.events.append(event)
        return self


class History(object):
    __slots__ = ('owner', 'ticks', 'current')
    """Holds snapshots and events per tick for its owner, to be used to report on the round."""
    def __init__(self, owner, tick: Tick):
        super().__init__()
        self.owner = owner
        self.ticks = defaultdict(TickHistory)
        self.current: TickHistory = self.ticks[tick]

    # ---------------------------------------------------------------------- QUERIES

    def get(self, key, default=None):
        return self.ticks.get(key, default)

    def __getitem__(self, item):
        assert item in self.ticks, f"{item} not found in History of {self.owner.name}"
        return self.ticks[item]

    def __contains__(self, item):
        return self.ticks.__contains__(item)

    def __iter__(self):
        return self.ticks.__iter__()

    def keys(self):
        return self.ticks.keys()

    @property
    def first(self):
        return sorted(self.ticks.keys())[0]

    @property
    def last(self):
        return sorted(self.ticks.keys())[-1]

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
        self.update()

    def set_tick(self, tick: Tick, update=True):
        assert isinstance(tick, Tick)
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
        result = defaultdict(int)
        for tick, th in self.ticks.items():
            result[tick] += th.hit_score
        return result


class FakeOwner(object):
    def __init__(self):
        self.snapshot = 'This is a snapshot'


if __name__ == '__main__':
    # t12 = Tick(1, 2)
    # print(t12, astuple(t12), t12.abs_tick, t12.round, t12.tick)

    # t29 = Tick(2, 9)
    # print(t29.next)

    # t34 = Tick(3, 4)

    t20 = Tick(2, 0)
    print(t20, astuple(t20), t20.abs_tick, t20.round, t20.tick)
    t20 = Tick.from_abs(20)
    print(t20, astuple(t20), t20.abs_tick, t20.round, t20.tick)

    t40 = Tick.from_abs(40)
    print(t40, astuple(t40), t40.abs_tick, t40.round, t40.tick)
    print(t40.prev)
    print(t40.next)

    # assert t29.next == Tick(3, 0)
    #
    # th = History(FakeOwner(), t12)
    # print(th.ticks)
    #
    # print(sorted((t29, t34, t12)))
    #
    # print(t34.ticks_for_round)