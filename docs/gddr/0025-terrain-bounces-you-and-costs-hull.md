# 0025. Running into terrain bounces you, and costs hull

**Status:** Accepted

## Context

A ring of five asteroids is the first terrain this game has, and it exists to make the middle of the
map a choice: go around the outside, or cut through and thread the gaps. That only works if hitting
one is a real cost and flying close to one is a real risk worth taking.

The mechanism is settled separately. A contact transmits an impulse and the object receiving it
decides what that means, and a tick advances by resolving encounters so contact is found partway
along a leg rather than at a tick boundary.
[ADR 0023](../adr/0023-a-tick-advances-by-encounters.md). What is left is the part a player feels:
how much speed a bounce keeps, what it does to the hull, and where it leaves you pointing.

Shields run 100 to 160 a face and warheads do 50 to 100, which is the band any damage number here
has to sit in to mean anything.

## Decision

**A bounce is a reflection that keeps the slide and gives back a third of the shove.**

```
n   = unit vector from the body's centre to the contact point
v_n = (v · n) n          driving into the surface
v_t = v − v_n            sliding along it
v'  = v_t − e · v_n      e = 0.3
```

A graze keeps almost all its speed and is nudged. A square hit comes back at a third of what it
arrived with. Nothing has to work out which of the two it is looking at, and a bounce can never
gain speed, because `|v'|² = |v_t|² + e²·|v_n|²` is at most `|v|²` for any `e` up to 1.

**Below an impact speed of 5, `e` is 0.** A mine drifting into an asteroid comes to rest against it
rather than bouncing forever at a smaller amplitude every time. Box2D calls this restitution slop.

**Damage is `mass × the normal component of the impact speed`**, where a standard hull is mass 1. So
a ship flying square into a rock at 45 loses 45, and a graze costs nothing, which matches what the
bounce does to its speed. It arrives as a `HitEvent` with the contact normal as its bearing, so
shields apply and going in head first lands on the bow shield.

**A bounce rewrites the heading, and `max_turn` does not apply.** Heading is the direction of travel,
so reflecting the velocity turns the ship however far the geometry says.

## Consequences

**Being turned is most of the punishment.** The hull damage is survivable; coming out of a collision
pointing somewhere you did not choose, halfway through a round you planned ten ticks of, is not.
Nobody commanded that turn, which is exactly why it is not limited by the helm.

**A plotted course survives a collision as fiction.** The remaining ticks were planned from a
heading the ship no longer has. The log draws what the ship actually did, so a player who clips an
asteroid on tick 3 spends the rest of the round somewhere they did not intend.

**Terrain is a tool if you learn the geometry.** A planet will come you about faster than the helm
allows, and clipping one is a way to dump speed in a hurry. That is a tactic the ring earns rather
than a hole in it, and it is the reason not to make the bounce punishing enough to be purely
avoided.

**A missile that hits terrain detonates, and a mine settles against it.** Each object decides what
the impulse means, so terrain is lethal to ordnance and merely inconvenient to a ship.

**You can shoot straight through a planet.** Terrain blocks movement and nothing else, so scans,
lasers and blasts ignore it. That is wrong and hiding behind a rock is worth having; it is on the
list in TODO.md rather than settled here.

**Nobody is ambushed by a rock.** A body's `visibility` is 300, so a scanner picks terrain up long
before it would pick up a ship of the same size.

## Alternatives rejected

**A fully elastic bounce, `e = 1`.** It hands out free speed. A planet becomes a slingshot, so the
fastest way across the ring is to aim at one, which turns terrain into a booster and rewards exactly
the play the ring is meant to discourage.

**A dead stop.** Flying into a planet then costs a round and nothing more, and the ring reads as a
wall to park against rather than something to fly around. It also throws away the sliding component,
so a ship grazing a planet at speed 45 loses all of it, which no player will accept as fair.

**Damage as kinetic energy, proportional to `v²`.** Physically honest and unplayable at this scale.
Against shields of 130 to 150 a square law runs from harmless to lethal across a narrow band of
speed, and the band moves every time a ship type is rebalanced.

**Limiting the bounce to `max_turn`.** It reads as consistent, and it makes a collision something
you can plan through: the ship comes out pointing roughly where it was going, so the cost is only
the hull. The turn is the punishment, and taking it away leaves the ring toothless.