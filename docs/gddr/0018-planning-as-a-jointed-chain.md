# 0018. A course is planned by dragging a jointed chain

**Status:** Accepted

## Context

A player's movement orders are turn and acceleration per tick: `2: R25`, `3: A-10`. Ten ticks a
round.

Writing that as text means simulating in your head where the ship ends up, which is what the
original play-by-mail game asked of people and what makes a first round hard.

## Decision

A round's path is a 10-segment polyline. Each segment's direction is that tick's heading and its
length is that tick's speed, both persisting forward until a command changes them.

That's exactly forward kinematics on a jointed chain. Drag a node, and the downstream nodes swing
rigidly along.

A drag sets that tick's turn and acceleration, clamped to the ship's limits. Orders are derived
from the shape rather than typed.

The client predicts the path exactly, because a ship's own course is deterministic from its own
commands. The engine stays authoritative.

## Consequences

Planning is direct. You see where the ship ends up while you drag it, without simulating anything
mentally.

The prediction is exact rather than approximate, because it runs the same arithmetic the engine
will. Anything involving other objects, like being hit, is not predicted at all.

Joints render back to front so tick 1 is on top. At a standstill all ten sit on the same point, and
grabbing tick 1 gives the whole chain speed at once.

Ticks sharing a position collapse into a labelled range, because a ship decelerating to a stop
parks every remaining tick on one spot and it reads as a single node otherwise.

Orders that aren't movement, like firing, are parsed out and re-emitted untouched, sorted by tick.
That shrinks as more of them become editable.

## Alternatives rejected

**A text box with validation.** What the console had. Honest, and it leaves the player doing
trigonometry to find out where they end up.

**Waypoints, with the engine solving the course.** Friendlier still, and it hides the turn and
acceleration limits that are the actual game. The limits should be felt while dragging, which is
why a node stops at them and turns red.

**The HTML drag API.** Built for dragging things between containers. Pointer events with
`setPointerCapture` give the precision an SVG canvas needs.
