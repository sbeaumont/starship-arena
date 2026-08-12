# 0019. Machines drive their components through one vocabulary

**Status:** Accepted

## Context

A machine is a bag of parts. `MachineInSpace.__init__` reads `defense`, `weapons`, `ecm` and
`control` off its type and attaches whatever it finds, asserting only that each one is a
`Component` (`machineinspace.py:76-89`). It never asks what any of them are.

That is the point of the whole arrangement. A missile carries a warhead today. Put something in
that heals, that teleports what it touches, that spawns a ship, and `Missile` should not change by
one line. Same for a ship: bolt on a part nobody has thought of yet, and the round processor keeps
running it.

Extensibility by composition is the goal the type objects and the component system exist to serve
(ADR 0003, ADR 0004). It only holds while a machine stays ignorant of what it is holding. One
method that reaches for a part by name or by class pins the design down at that spot, and every
new component after it has to be special-cased in the same place.

## Decision

Components answer a fixed set of questions, and a machine asks all of its components the same ones.

The vocabulary is what `Component` declares (`component.py:14-66`): `status`,
`expected_parameters`, `description`, `decide`, `tick`, `post_move`, `use_energy`, `activation`,
`reset`, `round_reset`, `post_round_reset`. Each has a neutral default on the base, so a component
stays silent about what does not apply to it.

The rules that follow from it:

**A machine iterates, it never indexes.** `Ship.tick` and `Ship.use_energy` loop
`all_components.values()` (`ship.py:181-192`). `Mine.decide` loops every weapon it carries
(`mine.py:43-45`), which is why `NanocyteMine` can hold a Splinter and a Nanocyte and have both go
off. No `isinstance`, no lookup by key, no `hasattr`.

**A new question goes on the narrowest base where it has a true answer, with a neutral default.**
`Weapon` already does this twice, and says so in the code (`weapon.py:9-14`):

```python
# Weapons that consume ammunition shadow this with a count of what is left.
ammo = None
# Weapons that put something into space shadow this with the type they launch.
payload_type = None
```

Anything of that kind may be asked. Most answer with the default. The ones for which the question
means something shadow it.

The default has to be an answer, not a placeholder, and that is what decides how far up it goes.
`Component.range = 0` belongs on the base because a cloak really does reach nowhere, and so does a
pilot. `ammo` sits one level down on `Weapon` because `None` there means the question does not
apply, and a component that cannot fire has nothing to say about ammunition.

**A question is named for what is being asked, never for the component that prompted it.** A
warhead that reaches 20 units and a repair field that reaches 20 units are the same question about
geometry, so the machine asks about reach. Name it `blast_range` and only a warhead can answer,
which means the repair field needs a second property and every caller has to know which to ask.

## Consequences

New behaviour is a component plus a registry line. `ShipSpawner` goes into a starbase's `weapons`
list and `Fire SS` works, because `FireCommand` resolves a component by name and calls `fire` on
whatever comes back.

Ask the live machine. `MachineType.weapons` is a property that builds fresh components on every
read (`missiles.py:17`, `mines.py:29`), so putting one of these questions on a type object
constructs a throwaway component to read a number off it, and gets no state at all.
`MineType.max_scan_distance` (`mines.py:18`) already does this and reports the wrong warhead.

This is a different rule from ADR 0010, and the difference decides which one applies. An identity
question is abstract on the base so a subclass cannot forget to answer. A capability question gets
a neutral default so a subclass need not care. `category_name` is the first kind, `ammo` is the
second.

The vocabulary grows, and each addition is a small tax on every component that will never use it.
That is the trade: a wider base buys machines that never need touching.

A component's own internals stay its own. `Shields.quadrant_of` and `Laser.can_fire_at` are called
by the component that owns them and by nothing else. The rule binds what the machine and the engine
ask across the seam, not what a component does inside itself.

### Where the code does not do this yet

Each of these is a spot where a new component or a new subclass would be silently ignored.

The ones that branch on a class carry an anchor comment at the site, and
`test/engine/test_vocabulary.py` fails on any that does not, so a new one cannot be added quietly
and a fixed one leaves an anchor pointing at nothing.

| | |
|---|---|
| `ADR0019-a` | `Gunner.lasers` filters weapons on `isinstance(weapon, Laser)`, so an NPC gunner can never fire anything else |
| `ADR0019-b` | `Gunner.decide` sorts targets by class, where `category_name` already answers it |
| `ADR0019-c` | `TickHistory.scans` filters events on `ScanEvent` |
| `ADR0019-d` | `TickHistory.hits` filters events on `HitEvent` |
| `ADR0019-e` | `TickHistory.non_scan_events`, the same question inverted |
| `ADR0019-f` | `TickHistory.add_event` branches on `ScanEvent` to deduplicate |
| `ADR0019-g` | `History.add_event` branches on `HitEvent` to score |

The five in `history.py` are one question asked five times: `Event.kind` is abstract on the base
([ADR 0010](0010-objects-describe-themselves.md)) and already answers it. Whether the fix is
reading `kind` or giving `Event` a question about what it counts towards is open.

Two more are not a class test and so have no anchor:

- `Missile.decide` reaches for one part by the literal key `'warhead'`. A missile with a second
  component never gets asked. `Mine` loops and is correct.
- `Warhead.explode` reads another object's `_type` for a question the object could answer.

`BoostCommand` was on this list and came off it. It found its shield with `isinstance(d, Shields)`; splitting the
boost parameter into a quadrant and an amount removed the override entirely, and there is no
`isinstance` left in `command.py`.

## Alternatives rejected

**A Protocol per capability.** `PayloadType` (`launcher.py:9`) declares what a launcher needs from
what it fires, so widening it looks like the obvious home for a new question. It is a contract kept
in two files that have to be edited together, and `runtime_checkable` makes it worse: `Commandable`
is one, so deleting `Ship.fire` makes `isinstance(ship, Commandable)` false and every ship's orders
are skipped in silence, with no error. The protocols that exist stay. New capabilities do not get
one.

**Asking the type object.** Type objects are shared and immutable (ADR 0003), and their component
lists are rebuilt on every read. A question about what a part does belongs to the attached,
stateful component, and the machine that holds it.

**`isinstance` at the call site.** It works, it is obvious, and it is the reason a `ShipSpawner`
would otherwise need `BoostCommand`, `Gunner` and `Missile.decide` all edited before it could
exist. Every spot on the list above is an argument that has already been lost once.

**Fewer, larger components.** Fold the behaviour into `Missile` and `Ship` and drop the component
seam. Cheaper today, and it gives up the thing the game is for: a new model is a registry class
that assembles existing parts in a new combination, and nothing else in the engine is told.