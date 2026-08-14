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


# How many places to try per body before calling a field unpackable. Well past what a field
# this game would play over needs, so hitting it means the numbers are wrong rather than the draw.
TRIES_PER_BODY = 200


def scatter(rng, count: int, width: float, height: float, apart: float,
            clear_of: list[tuple] = (), body: str = STANDARD_BODY) -> list[dict]:
    """Bodies dropped at random over a box centred on (0, 0), none nearer than `apart`."""
    placed = [(x, y) for x, y in clear_of]
    field = []
    for _ in range(TRIES_PER_BODY * count):
        if len(field) == count:
            return field
        # Rounded before it is checked, so what goes into the file is what was held apart.
        x = round(rng.uniform(-width / 2, width / 2))
        y = round(rng.uniform(-height / 2, height / 2))
        if any((x - px) ** 2 + (y - py) ** 2 <= apart * apart for px, py in placed):
            continue
        placed.append((x, y))
        field.append({'name': f"{body}-{len(field) + 1}", 'type': body, 'x': x, 'y': y})
    raise ValueError(f"Cannot fit {count} bodies {apart} apart in {width} by {height}: "
                     f"got {len(field)}.")