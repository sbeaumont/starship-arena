# 0020. An explosion damages everything in range

**Status:** Accepted

## Context

A warhead answers two separate questions. What sets it off, and what it does when it goes off.

`Warhead.triggers_on` filters by faction, so your ordnance is never set off by your own ship or
your own launches. `Warhead.explode` has always damaged every object within range, without asking
whose it is.

Making warheads trigger on the path travelled rather than at tick boundaries moved detonations
earlier, and the two rules started to collide in practice. In the `test-game` replay, a Rocket
fired on tick 1 goes off at x=102, and the Rocket fired from the same launcher on tick 2 is
sitting at x=82. That is exactly 20 apart, which is a `RocketWarhead`'s range, so the second
Rocket dies to the first. Any damage at all destroys a missile.

That raised the question of whether the blast should spare its owner.

## Decision

The trigger takes sides. The blast does not.

Nothing changes in `explode`: every object within range takes damage, including the ship that
fired, its other launches and its own mines.

## Consequences

Stacking launches at one target costs you. Firing the same launcher on consecutive ticks puts the
second round inside the first one's blast, so a player who wants both to arrive spaces them, aims
them apart, or accepts the loss.

Step 1's launch offset stops being a nicety. A payload born on its launcher is inside its own
blast, and the blast does not care that the launcher is friendly.

It cuts both ways in defence. Shooting down an incoming missile close to your own hull sets off
its warhead where it will hurt you, so range matters when a Gunner picks its moment.

A player who does not know the rule loses ordnance and cannot see why. The events say what hit
what, so the report shows it, but the reason has to be learned once.

## Alternatives rejected

**Filtering the blast by faction, as the trigger is filtered.** It reads consistent, and it is
worse to play. Stacked salvos would become strictly better than spaced ones, which removes a
decision from the game and makes the launcher a button rather than a weapon that wants aiming.
It is also a strange piece of physics to explain: an explosion that checks a transponder.

**Sparing only the firing ship, not its ordnance.** Half a rule. It still leaves a player wondering
why one thing survived and another did not, and it would make a ship's own hull a safe backstop to
detonate against.