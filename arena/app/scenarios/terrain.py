"""The terrain a scenario is played over.

A scenario says what its space is littered with, and more than one of them wants the same shape:
rocks spaced evenly around the middle, big enough to fly around and to hide a manoeuvre behind.
How far out, how many and which rock is the scenario's to say.
"""

from math import cos, radians, sin

# The ring everybody has learned to fly. A solo game is played over the same five rocks as the
# game is, so what a new commander practices against is what they will meet.
STANDARD_BODIES = 5

# How big a rock is belongs to the rock, not to the ring: it is a model constant on the body type
# in `registry/bodies.py`. Naming the type here is how a scenario picks a size.
STANDARD_BODY = 'Asteroid'


def asteroid_ring(radius: float, count: int = STANDARD_BODIES,
                  body: str = STANDARD_BODY) -> list[dict]:
    """Bodies spaced evenly around (0, 0), the first of them due north."""
    return [{'name': f"{body}-{n + 1}", 'type': body,
             'x': round(radius * sin(radians(n * 360 / count))),
             'y': round(radius * cos(radians(n * 360 / count)))}
            for n in range(count)]