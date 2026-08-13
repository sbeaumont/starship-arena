"""How today's object model becomes a version 1 document."""

from arena.engine.replay import Replay

# A machine answers all three. Terrain, never built, answers none.
CONDITION = ('hull', 'battery', 'components')


def document(replay: Replay) -> dict:
    """Every saved round of a played game, as the content of a v1 document."""
    objects: dict[str, dict] = dict()
    for tick in replay.ticks:
        for ois in replay.objects_at(tick).values():
            _recorded(objects, ois)['ticks'].append(_tick(ois.history[tick], tick.abs_tick))
    return {'first_tick': replay.first.abs_tick, 'last_tick': replay.last.abs_tick,
            'objects': list(objects.values())}


def _recorded(objects: dict, ois) -> dict:
    """The row this object is building up, opened the first time it turns up."""
    if ois.name not in objects:
        objects[ois.name] = {
            'name': ois.name,
            'type_name': ois.type_name,
            'category_name': ois.category_name,
            'faction': _side_of(ois),
            'owner': ois.owner.name if ois.owner else None,
            'player': ois.player if ois.is_player_controlled else None,
            'radius': ois.radius,
            'ticks': [],
        }
    return objects[ois.name]


def _tick(snapshot, abs_tick: int) -> dict:
    """One snapshot, as the tick it was."""
    return {
        'tick': abs_tick,
        'x': snapshot['pos'].x,
        'y': snapshot['pos'].y,
        'heading': snapshot['heading'],
        'speed': snapshot['speed'],
        'score': snapshot.score,
    } | _condition(snapshot) | {
        'scans': [{'name': s.name, 'x': s.pos.x, 'y': s.pos.y} for s in snapshot.scans],
        'events': [_event(e) for e in snapshot.non_scan_events],
    }


def _event(e) -> dict:
    """One event: what it was, what it carried, where, and what it manifested as."""
    return {'kind': e.kind, 'damage_type': str(e._type), 'text': str(e),
            'x': e.pos.x if e.pos else None, 'y': e.pos.y if e.pos else None,
            'shape': {e.shape.name: e.shape.measurements} if e.shape else dict()}


def _condition(snapshot) -> dict:
    """What a machine had left, and nothing where there was never a machine."""
    answered = [key for key in CONDITION if key in snapshot]
    if answered and len(answered) != len(CONDITION):
        raise ValueError(f"A snapshot answers {answered} of {CONDITION}, so a v1 document cannot "
                         f"say what it had left. Bring this translator up to date with the engine.")
    if not answered:
        return {'hull': None, 'battery': None, 'components': dict()}
    return {key: snapshot[key] for key in CONDITION}


def _side_of(ois) -> str | None:
    """Which side something is on. Ordnance reaches one through its owner, terrain has none."""
    return ois.faction or (ois.owner.faction if ois.owner else None)