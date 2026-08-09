"""Where a roster's ships start out.

A scenario says where its factions deploy, and most of them want the same shape: every faction the
same distance from the middle, its own ships in a clump around that, everybody looking inward. This
is that shape, on ship records, so what a scenario decides is written into `ships.jsonl` and replays
with the game. How far out is the scenario's to say.
"""

from collections import defaultdict
from math import atan2, cos, degrees, radians, sin

# Close enough to fly as a group, far enough apart that one blast is not the whole faction.
SPREAD = 20


def distribute_factions(ships: list[dict], rng, distance: float, spread: float = SPREAD,
                        face_middle: bool = True) -> list[dict]:
    """Spread the factions evenly around the middle, and point them at it.

    A record that carries coordinates keeps them; (0, 0) is what asks to be placed. Facing the
    middle is what stops a ship spending half its first round coming about, and a scenario where
    starting with your back to the game is the point says otherwise."""
    groups = defaultdict(list)
    for ship in ships:
        groups[ship.get('faction')].append(ship)
    centers = _ring(len(groups), distance, rng)
    placed = dict()
    for center, group in zip(centers, groups.values()):
        offsets = _ring(len(group), spread, rng)
        for ship, offset in zip(group, offsets):
            placed[ship['name']] = _deploy(ship, center, offset, face_middle)
    return [placed[ship['name']] for ship in ships]


def _ring(count: int, radius: float, rng) -> list[tuple]:
    """Points spaced evenly around (0, 0), the whole ring turned so nobody always gets north."""
    rotation = rng.uniform(0, 360)
    angles = [radians(rotation + i * 360 / count) for i in range(count)]
    return [(round(radius * cos(a)), round(radius * sin(a))) for a in angles]


def _deploy(ship: dict, center: tuple, offset: tuple, face_middle: bool) -> dict:
    x, y = ship.get('x', 0), ship.get('y', 0)
    if not (x or y):
        x, y = center[0] + offset[0], center[1] + offset[1]
    placed = dict(ship, x=x, y=y)
    if face_middle:
        placed['heading'] = round(degrees(atan2(-x, -y)) % 360, 1)
    return placed