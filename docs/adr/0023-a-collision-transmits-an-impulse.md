# 0023. A collision transmits an impulse

**Status:** Accepted. Contact per tick superseded by
[0024](0024-a-tick-advances-by-encounters.md)

## Context

A ring of five planets is the first terrain this game has. A solid body is untargetable,
immovable, indestructible and impassable, which settles everything about it except the one thing
that matters in play: what happens to whatever runs into it.

A tick is a jump. `move()` translates the whole speed at once, so a ship doing 45 has a leg rather
than a position, and contact has to be found along that leg. The geometry already exists:
`ObjectInSpace.approach_fraction` answers how far into a tick the gap between two legs first closed
to a given distance, which is what the surface of a body is, and `position_at` turns the answer
back into a point. The game development field calls this swept, or continuous, collision detection.

The engine also already has the shape for "something happened to you, work out what it means".
`take_damage_from(hit_event)` hands an object an event and lets the object decide: a ship runs it
through its shields, a missile dies to any damage at all, a starbase soaks it. Nothing in `Warhead`
knows what a shield is. That is ADR 0019 applied one level up, to objects instead of components.

Two constraints bound what can be decided here. Rounds are deterministic, with no clock and no
random numbers (ADR 0002). And the order objects are processed in must never change the outcome of
a tick, which is why only static bodies are in scope: `GameRound.do_tick` moves everything in one
loop, so a ship bouncing off another ship would resolve differently depending on which of the two
came first.

## Decision

**A collision transmits an impulse, and the object that receives it decides what that means.**

An impulse is a direction and a magnitude. A body produces one when something reaches its surface.
The receiving object answers for itself, the way it already answers `take_damage_from`: a ship
bounces and takes damage, a missile detonates, a mine settles against the surface, a starbase
ignores it the way it already ignores `turn` and `accelerate`.

The hook is named for the impulse rather than for the collision. A tractor or repulsor weapon
transmits the same thing from a different source, and a hook called `collide` would either be
called by something that is not a collision or grow a parallel path beside it.

### The bounce

Split the incoming velocity into the part driving into the surface and the part sliding along it,
and touch only the first:

```
n   = unit vector from the body's centre to the contact point
v_n = (v · n) n          driving into the surface
v_t = v − v_n            sliding along it
v'  = v_t − e · v_n      e is the coefficient of restitution
```

`e = 0.3`. A graze keeps almost all its speed and is nudged, a square hit comes back at a third of
what it arrived with, and no code has to work out which of the two it is looking at.

Below an impact speed of 5, `e` is 0. A mine drifting into a planet comes to rest against it
instead of bouncing forever at ever smaller amplitudes. Box2D calls this restitution slop.

This engine holds heading and speed rather than a velocity, and the conversion between the two
belongs to `Vector`. Anything that reaches for `sin` and `cos` to work out where something is
going has taken a copy of a fact `Vector` owns.

A bounce can never exceed `max_speed`, because `|v'|² = |v_t|² + e²·|v_n|²`, which is at most
`|v|²` for any `e` up to 1. Reflection only ever takes speed away. Nothing has to clamp it, and a
player who wants to shed speed fast may deliberately clip a planet to do it.

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

### Placement, damage and timing

The object is placed just outside the surface, never on it, so floating point cannot leave it a
hair inside and colliding again next tick. This is the problem `MIN_GAP` already solves for a
warhead's bearing, and it gets the same answer.

Damage is `mass × the normal component of the impact speed`, where a standard hull has mass 1. A
graze costs nothing, which matches the bounce. It goes through `HitEvent` so shields apply, with
the contact normal as the bearing, so flying head first into a planet lands on the bow shield.

One contact per object per tick, resolved at the earliest contact fraction, the way
`Warhead.contact_fraction` already picks `min` over everything it could go off against. Nothing
chains within a tick.

### Belonging to no faction is its own answer

Faction has three answers, and only two of them were ever asked for. Mine, someone else's, and
none at all. `Warhead.triggers_on` and `GuidedMissile.scan` both compare faction strings, so a
missing faction reads as an enemy one and terrain becomes a target.

Something that belongs to no faction is neither tracked nor triggered on. The object answers that
about itself, rather than every caller comparing strings and getting it wrong in its own way.

A missile that runs into a body still detonates, through the impulse rather than through the
trigger. Contact is what sets it off, which needs no faction question answered at all.

## Consequences

**A bounce turns a ship further than it can turn itself.** Heading is the direction of travel here,
so reflecting the velocity rewrites the heading, with no regard for `max_turn` (`ship.py:119`).
That is most of the punishment for hitting a planet, and it is correct: nobody commanded the turn.
A player who learns the geometry can use a planet to come about faster than the helm allows, or to
dump speed, and that is a tactic the ring earns rather than a hole in it.

**A plotted course survives a collision as fiction.** The remaining ticks of a round were planned
from a heading the ship no longer has. The course is drawn from what the ship actually did, so the
log will show it, and a player who clips a planet on tick 3 spends the rest of the round somewhere
they did not intend.

**Ship against ship stays out.** The order defect in TODO.md has to be fixed first. Until then a
collision is only ever against something that does not move, which is what keeps the outcome
independent of iteration order.

**A push weapon costs a component and nothing else.** It produces an impulse and every object type
already knows what to do with one. That is the whole reason for the naming. It is also the one
thing that can push a ship past `max_speed`, since adding velocity grows the magnitude where
reflecting it cannot, so the bleed-off rule belongs with that weapon rather than here.

**Line of sight waits.** A body blocks movement in this decision and nothing else, so scans, lasers
and blasts pass through a planet as though it were empty space. That is wrong, and hiding behind a
planet is worth having, so it is on the list in TODO.md rather than settled here.

## Alternatives rejected

**A fully elastic bounce (`e = 1`).** It hands out free speed. A planet becomes a slingshot, and
the fastest way across the ring is to aim at one, which turns terrain into a booster and rewards
exactly the play the ring is meant to discourage.

**A dead stop.** Flying into a planet then costs a round and nothing more, and the ring reads as a
wall to be parked against rather than something to be flown around. It also throws away the sliding
component, so a ship grazing a planet at speed 45 loses all of it, which no player will accept as
fair.

**Naming the hook `collide`.** The push weapon then calls a method named for something that did not
happen, or gets its own method that does the same arithmetic and drifts out of step with this one
the first time `e` changes.

**Modelling the body as infinite mass in the arithmetic.** `m2/(m1+m2)` with a literal infinity is
`inf/inf`, which is NaN, and a NaN heading propagates silently through a whole round before
anything looks wrong. The body already knows it is immovable.

**Damage as kinetic energy, proportional to `v²`.** Physically honest and unplayable at this scale.
With shields at 130 to 150 and warheads at 50 to 100, a square law runs from harmless to lethal
across a narrow band of speed, and the band moves every time a ship type is rebalanced.

**An iterative solver, resolving contacts until nothing overlaps.** What Box2D and Bullet do, and
they are stepping continuous time at 60 Hz. Ten discrete ticks with a hard determinism rule want
one closed-form answer per contact. Iterating also reintroduces order dependence through the back
door, because which contact is solved first changes where everything ends up.