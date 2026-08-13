"""A file out of Valhalla, as the picture a replay is watched through.

The mirror of `GameService.game_replay`, which builds the same `GameReplay` off a played game's
saved worlds: one pass over the ticks, a side's own objects as they were and everything else as
the sightings its commanders took. Two walks, one shape, so the map above them never learns which
shelf a game came off. `test/app/test_the_museum.py` holds the two together.

One builder per version of the format, because a version once written is never reinterpreted.
See docs/adr/0034-a-finished-game-is-exported-to-a-schema-of-its-own.md.
"""

from collections import defaultdict

from arena.engine.history import Tick
from arena.app.dto import Beam, GameReplay, ObjectTick, ReplayObject, TickEvent
from arena.app.valhalla import v1


def replay(document: dict, faction: str | None = None) -> GameReplay:
    """A finished game as one side saw it, or as all of them together when no side is named."""
    return _BUILDERS[document['version']](document, faction)


def _v1(document: dict, faction: str | None) -> GameReplay:
    rows = {o['name']: o for o in document['objects']}
    mine = {name: o for name, o in rows.items() if faction is None or o['faction'] == faction}
    if faction is not None and not mine:
        raise ValueError(f"No faction {faction} ever flew in {document['game']}.")

    objects: dict[str, ReplayObject] = dict()
    beams: dict[tuple, Beam] = dict()
    at_tick = _at(document)
    for at in _ticks(document):
        in_space = [(name, row) for name, row in at_tick[at.abs_tick] if name in mine]
        for name, row in in_space:
            _recorded(objects, rows[name], contact=False).path.append(
                ObjectTick(abs_tick=at.abs_tick, x=row['x'], y=row['y'],
                           heading=row['heading'], speed=row['speed']))
            objects[name].events.extend(
                TickEvent(tick=at.tick, abs_tick=at.abs_tick, text=e['text'], kind=e['kind'])
                for e in row['events'])
            _beams_in(row, at, beams)
        if faction is None:
            continue
        # What the side saw of everything else, off the ships whose scans a faction shares.
        # Several of them see the same object, so a tick gets one point however many looked.
        for name, row in [(n, r) for n, r in in_space if rows[n]['player']]:
            for scan in row['scans']:
                if scan['name'] in mine:
                    continue
                seen = _recorded(objects, rows[scan['name']], contact=True)
                if not seen.path or seen.path[-1].abs_tick != at.abs_tick:
                    seen.path.append(ObjectTick(abs_tick=at.abs_tick, x=scan['x'], y=scan['y'],
                                                heading=None, speed=None))
    return GameReplay(game=document['game'], faction=faction,
                      first_tick=document['first_tick'], last_tick=document['last_tick'],
                      objects=list(objects.values()), beams=list(beams.values()))


def _ticks(document: dict) -> list[Tick]:
    """Every tick the game holds, in order, which is what a playhead scrubs over."""
    return [Tick.from_abs(abs_tick)
            for abs_tick in range(document['first_tick'], document['last_tick'] + 1)]


def _at(document: dict) -> dict[int, list[tuple[str, dict]]]:
    """What was in space at each tick, since a file is written per object rather than per tick.

    A tick an object has no row for is a tick it was not in space, which is the whole of the rule.
    """
    in_space = defaultdict(list)
    for o in document['objects']:
        for row in o['ticks']:
            in_space[row['tick']].append((o['name'], row))
    return in_space


def _recorded(objects: dict, o: dict, contact: bool) -> ReplayObject:
    """The row this object is building up in a replay, opened the first time it turns up."""
    if o['name'] not in objects:
        objects[o['name']] = ReplayObject(
            name=o['name'], type_name=o['type_name'], category_name=o['category_name'],
            faction=o['faction'], owner=o['owner'], radius=o['radius'],
            contact=contact, path=[], events=[])
    return objects[o['name']]


def _beams_in(row: dict, at: Tick, into: dict) -> None:
    """Blows that ran along a line, keyed so the shooter's copy and the target's are one.

    A shape is what an event manifested as, under its own name and its own measurements, so this
    asks whether one is a line rather than what sort of event was carrying it."""
    for e in row['events']:
        line = e['shape'].get('line')
        if line:
            into.setdefault(
                (at.abs_tick, line['x1'], line['y1'], line['x2'], line['y2']),
                Beam(tick=at.tick, abs_tick=at.abs_tick,
                     x1=line['x1'], y1=line['y1'], x2=line['x2'], y2=line['y2'],
                     damage_type=e['damage_type']))


_BUILDERS = {v1.VERSION: _v1}