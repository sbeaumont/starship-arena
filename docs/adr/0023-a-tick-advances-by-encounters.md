# 0023. A tick advances by encounters, and contact transmits an impulse

**Status:** Accepted

## Context

A tick is a jump. `move()` translates the whole speed at once, so a ship doing 45 has a leg rather
than a position, and not everything gets to fly its whole leg.

A surface ends one where it is met. A warhead ends one where it goes off. A tractor beam or a
trigger field will do the same. All of them are one question: **when does something come within a
range that matters?** The geometry to answer it already exists.
`ObjectInSpace.approach_fraction` answers how far into a tick the gap between two legs first closed
to a given distance, and `position_at` turns the answer back into a point. Game development calls
this swept, or continuous, collision detection.

The question has to be answered before anything moves, because an object that has not had its turn
yet still sits at the start of its leg, and between the last thing that can change a vector and the
first thing that moves is the only moment when what happens to whom is a fact rather than an
accident of iteration order.

It has to be answered once. Scanning records where things are, `decide` acts on what it finds, and
the snapshot is what a player is shown. Anything deciding where an object stopped after those have
run leaves them disagreeing, and the disagreement is what a player sees.

And a blast has to catch who was there when it went off, so "where was this object at that fraction
of the tick" must have an answer for something that stopped early as well as for something that
flew its whole leg.

Then there is what a contact *does*. The engine already has the shape for "something happened to
you, work out what it means". `take_damage_from(hit_event)` hands an object an event and lets the
object decide: a ship runs it through its shields, a missile dies to any damage at all, a starbase
soaks it. Nothing in `Warhead` knows what a shield is. That is
[ADR 0019](0019-machines-drive-components-through-one-vocabulary.md) applied one level up, to
objects instead of components.

Two constraints bound all of it. Rounds are deterministic, with no clock and no random numbers
([ADR 0002](0002-deterministic-rounds.md)). And the order objects are processed in must never
change the outcome of a tick.

## Decision

### A tick advances by resolving encounters

**An encounter is something coming within a range that matters, at a fraction of the tick.**

```
loop:
    ask       every object with tick left for its first encounter
    stop      when none is found
    resolve   everything at the earliest fraction, moving what it touches there
move          everything left the rest of its leg
```

Only the earliest fraction resolves each time round. A later encounter is a prediction made against
a world the earlier one is about to change: it can destroy what was going to be met, or put
something in the way that was not there when the question was asked.

**Nothing advances past a fraction while anything is still pending at or before it.** That is what
makes the rest work, and it is why objects without an encounter do not move: an object that has not
moved is already complete, so nothing has to be remembered on its behalf.

- One that has not moved has its whole leg ahead of it, and its position at any fraction is on it.
- One stopped at `f` stands at `f`, and the segment it just flew is `moved_from → pos`.

A segment is discarded only once nothing can still ask about it. No object holds a history of its
own tick.

Within one fraction, encounters resolve in name order, so which object the world happens to list
first cannot decide anything.

### Who answers

Answers compose, and the earliest wins:

| asked | answers |
|---|---|
| `ObjectInSpace` | the first solid surface its leg reaches, and the impulse that brings |
| `MachineInSpace` | that, or the earliest any of its components names |
| `Component` | none, the neutral default |
| `Warhead` | the fraction it goes off at |

That is ADR 0019 applied to time: a machine asks all of its components the same question and names
none of them.

### Why it ends

Two statements, and neither depends on how a scenario is laid out.

**Everything at a fraction resolves together.** A missile can reach a surface and trigger on a foe
at the same moment, and both are real. Resolving one and leaving the other would leave an encounter
at the fraction the object now stands on.

**An object that has not advanced once its fraction resolved is done for the tick.** Bounced off one
surface straight into another, it is wedged, and spending the rest of the tick there is what being
wedged is. Each pass therefore either advances an object or finishes it.

### A position part way through a tick

`ObjectInSpace.position_at(fraction)` answers where it was that far into **the tick**. The object
knows how much of the tick it has used; that is per-tick state of the same kind as `moved_from`,
written by `move` and meaningless on its own.

`Leg.position_at` is a fraction of that leg and nothing more. The two agree only for something that
flew its whole leg, and a caller that wants a moment in a tick wants the object.

### Contact transmits an impulse, and the receiver decides

An impulse is a direction and a magnitude. A body produces one when something reaches its surface.
The receiving object answers for itself, the way it already answers `take_damage_from`: a ship
bounces and takes damage, a missile detonates, a mine settles against the surface, a starbase
ignores it the way it already ignores `turn` and `accelerate`.

The hook is named for the impulse rather than for the collision. A tractor or repulsor weapon
transmits the same thing from a different source, and a hook called `collide` would either be
called by something that is not a collision or grow a parallel path beside it.

What a bounce actually does to a ship, the restitution and the damage, is a game design decision
and lives in [GDDR 0025](../gddr/0025-terrain-bounces-you-and-costs-hull.md).

This engine holds heading and speed rather than a velocity, and the conversion between the two
belongs to `Vector`. Anything that reaches for `sin` and `cos` to work out where something is going
has taken a copy of a fact `Vector` owns. The body works the impulse out, so restitution never
leaves the body and no receiver ever sees a coefficient.

### The body does not move, and says so

The two-body form of the same equation scales each side by `m2/(m1+m2)` and `m1/(m1+m2)`. As the
body's mass grows without bound those go to 1 and 0, and what is left is the formula above. So a
body that is asked whether it moves, and answers no, needs no arithmetic on infinity and no second
code path. Ship against ship later is this equation with the ratios put back.

`mass` goes on `ObjectInSpace` and defaults to 0, because anything in space could have one and
plenty of things later will not: a pickup or a powerup is massless and should pass through the
arithmetic without a special case. A machine takes its mass from its type, the way it takes its
hull. `max_hull` cannot stand in for it, since a large fragile hull is not a heavy one.

Being immovable is effectively infinite mass, and it is one fact rather than a rule per class. A
starbase is bolted down for the same reason a planet is, so both answer the same question and
neither needs a collision rule written for it.

`radius` says things stop at me, `mass` says I can be shifted, and both default to nothing. Solidity
and immovability are numbers an object carries rather than classes of object, which is why there is
no `SolidBody` type and no `is_solid` anywhere.

### Placement

The object is placed just outside the surface, never on it, so floating point cannot leave it a hair
inside and colliding again next tick. This is the problem `MIN_GAP` already solves for a warhead's
bearing, and it gets the same answer.

### Belonging to no faction is its own answer

Faction has three answers, and only two of them were ever asked for. Mine, someone else's, and none
at all. Comparing faction strings reads a missing faction as an enemy one, which makes terrain a
target.

`Stance` is `Friend`, `Foe` or `Neutral`, and the object answers it about itself rather than every
caller comparing strings and getting it wrong in its own way. Excluding yourself falls out: a thing
is its own `Friend`, so a warhead cannot go off on its own launcher.

A missile that runs into a body still detonates, through the impulse rather than through the
trigger. Contact is what sets it off, which needs no faction question answered at all.

## Consequences

**One rule, one shape.** Nothing that shortens a leg has a phase of its own, and `place_at` means
only what it says: putting something somewhere it did not travel to.

**A new encounter is a component.** A tractor beam, a minefield trigger, a jump inhibitor: a class
answering one question, with no phase touched and nothing in `GameRound` edited.

**Chain reactions are order-independent.** A blast at `0.4` destroys a missile, and that missile's
warhead goes off at `0.4`, because the next pass asks from there. Whether it chains no longer
depends on which object the world happens to list first.

**A blast catches who was actually there**, including objects that had not moved yet.

**Warheads trigger on the leg an object is about to fly.** The answer is the same as on the leg it
flew, and it is the earlier one that anything else can see.

**A missile launched this tick flies its first leg whole.** Weapons fire after the question has been
asked, so nothing was there to answer for it.

**A push weapon costs a component and nothing else.** It produces an impulse and every object type
already knows what to do with one. That is the whole reason for the naming. It is also the one thing
that can push a ship past `max_speed`, since adding velocity grows the magnitude where reflecting it
cannot, so the bleed-off rule belongs with that weapon rather than here.

**Being stuck is an outcome, not an error.** It has to be reachable in a test, because nothing in a
five-asteroid ring can produce it and a station with an inlet will.

**Per-tick state can disagree with itself.** How far it has travelled and where it travelled from
are two facts about one move, written in one place for that reason.

**Ship against ship stays out.** The processing-order defect in TODO.md has to be fixed first. Until
then a contact is only ever against something that does not move.

**Line of sight waits.** A body blocks movement and nothing else, so scans, lasers and blasts pass
through a planet as though it were empty space. That is wrong, and hiding behind a planet is worth
having, so it is on the list in TODO.md rather than settled here.

**What a contact feels like is decided elsewhere.** The restitution, the damage and the fact that a
bounce turns a ship further than the helm can are in
[GDDR 0025](../gddr/0025-terrain-bounces-you-and-costs-hull.md). This decision is the mechanism, and
a change to either should not need the other reopened.

## Alternatives rejected

**One contact per object per tick**, which is what this decision said before encounters existed. A
leg that can be cut only once cannot express a missile that stops at a surface and goes off there,
nor a bounce into a second surface. The rule existed to bound the work, and the two statements under
*Why it ends* bound it without capping it. It was also read at the time as ruling out any iterative
resolution, on the grounds that which contact is solved first changes where everything ends up. That
is only true of a solver that picks an order. Resolving strictly by earliest fraction, and every
encounter at that fraction together, has no order to pick.

**Advancing the whole population to the earliest encounter**, keeping a global clock. The same
answers, reached by moving everything repeatedly. An object with nothing in its way is already
complete where it stands, so moving it early buys nothing and costs the state to describe where it
got to.

**Letting each object advance to its own next encounter.** More parallel, and it admits an object
getting ahead of an encounter that concerns it. Then a blast behind it needs a segment it has left,
so every object carries a history of its own tick, or is rewound into one.

**Refusing an encounter at the fraction an object already stands on.** It reads like a guard against
looping, and it rejects two legitimate cases: a surface and a trigger at one moment, and a wedge.

**A warhead moving its container after the fact.** It reaches the right position by the time the
snapshot is taken, and everything that ran in between saw a different one. Reports are built from
what was seen, so a player is shown a missile flying past what it destroyed.

**Correcting the sightings a warhead invalidated.** An object reaching into other objects' histories
to edit what they saw. Nothing else in the engine may do that.

**Repairing it above the seam, by dropping a sighting an explosion contradicts.** One symptom
hidden, two phases still disagreeing, and the next thing that shortens a leg reproduces it somewhere
else with nothing to point at.

**Moving scanning after `decide`.** `GuidedMissile.scan` sets the target that `decide` intercepts,
so the two cannot swap.

**Naming the hook `collide`.** The push weapon then calls a method named for something that did not
happen, or gets its own method that does the same arithmetic and drifts out of step with this one
the first time `e` changes.

**Modelling the body as infinite mass in the arithmetic.** `m2/(m1+m2)` with a literal infinity is
`inf/inf`, which is NaN, and a NaN heading propagates silently through a whole round before anything
looks wrong. The body already knows it is immovable.