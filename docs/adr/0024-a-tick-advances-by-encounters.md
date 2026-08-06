# 0024. A tick advances by encounters

**Status:** Proposed

Replaces two statements in [ADR 0023](0023-a-collision-transmits-an-impulse.md): that an object
takes one contact per tick, and that an iterative resolution reintroduces order dependence.

## Context

A tick is a jump, and not everything gets to finish it. A surface ends a leg where it is met. A
warhead ends one where it goes off. A tractor beam or a trigger field will do the same. All of them
are one question: **when does something come within a range that matters?**

It has to be answered before anything moves. ADR 0023 settles why: between the last thing that can
change a vector and the first thing that moves, every leg is known and no position has changed, and
that is the only moment when what happens to whom is a fact rather than an accident of iteration
order.

It has to be answered once. Scanning records where things are, `decide` acts on what it finds, and
the snapshot is what a player is shown. Anything deciding where an object stopped after those have
run leaves them disagreeing, and the disagreement is what a player sees.

And a blast has to catch who was there when it went off, so "where was this object at that fraction
of the tick" must have an answer for something that stopped early as well as for something that
flew its whole leg.

## Decision

**An encounter is something coming within a range that matters, at a fraction of the tick. A tick
advances by resolving encounters.**

```
loop:
    ask       every object with tick left for its first encounter
    stop      when none is found
    resolve   everything at the earliest fraction, moving what it touches there
move          everything left the rest of its leg
```

Only the earliest fraction resolves. A later encounter is a prediction made against a world that
the earlier one is about to change: it can destroy what was going to be met, or put something in
the way that was not there when the question was asked.

**Nothing advances past a fraction while anything is still pending at or before it.** That is what
makes the rest work, and it is why objects without an encounter do not move: an object that has not
moved is already complete, so nothing has to be remembered on its behalf.

- One that has not moved has its whole leg ahead of it, and its position at any fraction is on it.
- One stopped at `f` stands at `f`, and the segment it just flew is `moved_from → pos`.

A segment is discarded only once nothing can still ask about it. No object holds a history of its
own tick.

### Who answers

Answers compose, and the earliest wins:

| asked | answers |
|---|---|
| `ObjectInSpace` | the first solid surface its leg reaches, and the impulse that brings |
| `MachineInSpace` | that, or the earliest any of its components names |
| `Component` | none, the neutral default |
| `Warhead` | the fraction it goes off at |

That is [ADR 0019](0019-machines-drive-components-through-one-vocabulary.md) applied to time: a
machine asks all of its components the same question and names none of them.

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

**Being stuck is an outcome, not an error.** It has to be reachable in a test, because nothing in a
five-asteroid ring can produce it and a station with an inlet will.

**Per-tick state can disagree with itself.** How far it has travelled and where it travelled from
are two facts about one move, written in one place for that reason.

## Alternatives rejected

**One contact per object per tick**, as ADR 0023 had it. A leg that can be cut only once cannot
express a missile that stops at a surface and goes off there, nor a bounce into a second surface.
The rule existed to bound the work, and the two statements above bound it without capping it.

**Advancing the whole population to the earliest encounter.** The same answers, reached by moving
everything repeatedly and tracking a global clock. An object with nothing in its way is already
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