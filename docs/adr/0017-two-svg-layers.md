# 0017. The map is two SVG layers, world and screen

**Status:** Accepted

## Context

The tactical map pans and zooms across a world hundreds of units wide. It has to show ship markers,
labels, blast radii, tracks and a grid.

Two things pull in opposite directions. A marker should stay the same size on screen at any zoom,
or it becomes a dot or a blob. A blast radius is a real distance and must scale, or it lies about
what it covered.

Labels bring a third problem: they overlap, and text scaled by a zoom transform is unreadable at
both ends.

## Decision

Two stacked SVG elements.

**Layer one is world coordinates** and carries all geometry. Its `viewBox` is driven by a camera of
`{cx, cy, upp}`, where `upp` is world units per screen pixel.

**Layer two is screen pixels**, `viewBox="0 0 width height"`, `pointer-events: none`, and holds
every piece of text plus its leader lines.

Anything that should look constant is sized `px * upp`. Anything that is a real distance is drawn
in world units and scales.

Label de-overlap is a greedy downward nudge using monospace metrics, with a leader line drawn when
a label had to move.

## Consequences

Markers, arcs and handles stay the same size at any zoom, and blast circles honestly cover what
they covered.

Text is never transformed, so it's always crisp, and de-overlap arithmetic is in the same units as
the text.

Font sizes are JavaScript constants passed as `font-size` attributes rather than CSS, so the
de-overlap maths cannot drift from what's rendered.

Everything drawn in the pixel layer needs a world-to-screen conversion. That's the cost, and it's
one function.

## Alternatives rejected

**One layer with counter-scaled text.** Scale every label by `1/zoom`. It works, it makes text
blurry at fractional scales, and label collision has to be computed in world units that change
meaning as you zoom.

**Canvas.** Faster for thousands of objects, and it gives up hit testing, accessibility and being
able to read the markup. A busy round is around a hundred objects.
