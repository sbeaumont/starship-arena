# Event levels in the log

A line is shown without being asked for when its `kind` is not `internal`, and coloured by that
same `kind`. One name decides both things. The replenish message is what made that visible: it had
to become a kind of its own to be read at all.

Parked on a naming decision. Nothing here is urgent.

## What exists to build on

`Event.kind` is an abstract property each subclass answers, the way `ObjectInSpace.category_name`
does, and it already reaches the browser: `TickHistory.non_scan_events` passes everything but a
scan through, `services` copies `e.kind` onto `TickEvent`, and `LogPanel` sets each line's CSS
class from it. A new kind costs one colour rule, and a kind with no rule reads as dim.

`InternalEvent` is the base for anything message-shaped: no location, no source, one string.
`ReplenishEvent` subclasses it and answers a different `kind`.

## The fact that decides the shape

**A `HitEvent` is one object in two ships' histories.** `Laser.fire` adds it to the shooter
and `Ship.take_damage_from` adds that same object to the target.
`Warhead.explode` does both as well. The text reads identically in both logs.

So tone cannot live on an event. That one object is a triumph in one log and a disaster in the
other, and whichever value it carried would be wrong for one of its two readers. Tone is a
function of the event *and* whoever is reading it.

That is the argument against an `InfoEvent` carrying `positive | neutral | negative`. It would
work only for messages that live in exactly one history, and miss the events with the most tone in
them. If tone is ever wanted for hits, it belongs where the reader is known, which is the services
layer building `TickEvent` for a particular player.

## Where the thinking landed

`kind` is already the enum the log-level idea wants: a per-subclass string interfaces key off. So
`warning` can be added to it with no second axis and no new field on `TickEvent`.

| kind | level | colour | what it is |
|---|---|---|---|
| `internal` | debug | dim | energy, movement, "executing command" |
| `warning` | warning | amber | a refused order |
| ? | good news | green | a replenish |
| `hit` | — | red | unchanged |
| `explosion` | — | amber | unchanged |
| `scan` | — | — | never reaches the log |

## Open

- **What the positive level is called.** The log-level scale has no word for good news, which is
  why `replenish` is sitting in that row today.
- **Whether a refusal becomes a warning.** `CommandSet.add` records one as an `InternalEvent`, so
  it is debug-level and sits behind "every message". Every rejected `Fire R2` on Pi-tje was in the
  log and unread. This is the part with a cost today, and it changes what every game shows.
- **Whether `hit` and `explosion` stay kinds of their own.** Both come from outside. They are kept
  apart because a reader has more to say about them than that they happened, and because each
  carries a colour.

## What it would touch

`Event` subclasses in `arena/engine/objects/event.py`, the comment on `TickEvent.kind`, the
`Event` entry in `docs/glossary.md`, the kinds line in `docs/information.md`, and the `li.<kind>`
rules in `LogPanel.svelte`. No DTO field and no change to the filter, as long as `internal` stays
the one kind that is hidden.