# 0011. Snapshots hold values, never references

**Status:** Accepted

## Context

Each tick, every object records a snapshot into its history: position, heading, speed, hull,
battery, and what every component reports. That history is what the round report, the map, the log
and any future replay all read.

`Ship.snapshot` used to do `self.defense.copy()`, which copies the list and shares the component
objects inside it. So all ten ticks held the same `Shields` object.

The effect: a ship whose east shield dropped at tick 10 reported the damaged value at every tick,
including before it was hit. The history said the shield was down from the start of the round. It
had been wrong that way for every round ever recorded.

## Decision

A snapshot holds values. Anything mutable is copied by value at the moment of recording:

```python
snap['components'] = {name: dict(c.status) for name, c in self.all_components.items()}
```

Each level of the hierarchy adds exactly what it owns and passes the rest up.

## Consequences

The history is true per tick. Shields drop when they were hit, ammo falls on the tick a shot was
fired, and a tick slider over a round becomes possible.

Snapshots are bigger, because they hold copies. At ten ticks per round for a few dozen objects,
that doesn't matter.

Every new field on a snapshot has to be checked for this. A mutable object put in by reference will
look right in the round it was written and lie about every earlier tick.

Changing the shape of a snapshot invalidates saved games, which is fine because [they're
regenerable](0002-deterministic-rounds.md).

## Alternatives rejected

**Deep-copying whole objects into the history.** Correct, and it drags the entire object graph into
every tick of every pickle, including owners and targets. Components already report their state as
plain values; copying that is enough.

**Reconstructing history by replay instead of storing it.** Attractive, and a real option later
given determinism. It's a much larger change than fixing the copy, and the snapshot has to be right
either way.
