# Game design decisions

How the game is played: what a player is allowed to know, what a weapon does, what an order feels
like to give. The interface counts as game design when it decides how the game is played, and as an
[architecture decision](../adr/) when it is about the technology underneath.

**Decisions about how the thing is built live in [`../adr/`](../adr/)**, and the two share one run of
numbers, so a reference to 0020 is unambiguous and nothing is ever renumbered. A gap here is a
number the other family holds, or one that merged into another record.

One decision per file, numbered in the order they were accepted.

| | |
|---|---|
| [0012](0012-open-information.md) | Ship statistics are public |
| [0013](0013-fog-of-war-from-scans.md) | Fog of war is faction-shared and derived from scans |
| [0018](0018-planning-as-a-jointed-chain.md) | A course is planned by dragging a jointed chain |
| [0020](0020-explosions-do-not-take-sides.md) | An explosion damages everything in range |
| [0025](0025-terrain-bounces-you-and-costs-hull.md) | Running into terrain bounces you, and costs hull |
| [0028](0028-deadlines-are-part-of-the-game.md) | A round lands on the clock, and missing it costs you the round |

## What belongs here

A decision belongs here when a player would notice it being reversed. Ship statistics being public
changes how a game is won. An explosion sparing its owner changes whether stacking a salvo is free.
Which directory `arena/app/scenarios/` sits in does not.

The line is not always clean and the file only lives in one place. Where a decision is both, file it
by what it is *for*: dragging a jointed chain is here because it decides that a player feels the
turn and acceleration limits rather than being handed a solved course, even though half of its
argument is about pointer events.

## Template

Same shape as an ADR, because the value is in the last section either way.

```markdown
# NNNN. Title in the present tense

**Status:** Accepted

## Context
What forced a decision. What the game did before, and what was wrong with it.

## Decision
What happens now. Present tense, specific, with the numbers.

## Consequences
What it costs and what it buys, including what a player has to learn the hard way.

## Alternatives rejected
What else was considered, and why it lost. Be concrete about how the other one plays.
```

**Say how the rejected one plays, not just that it lost.** "A fully elastic bounce was rejected"
prevents nothing. "A fully elastic bounce makes a planet a slingshot, so the fastest way across the
ring is to aim at one, which rewards exactly the play the ring exists to discourage" stops the next
person proposing it.

The numbers matter here in a way they do not in an ADR. A restitution of 0.3 is a decision, and
somebody who changes it to 0.8 should find out from this file what that does to the game.