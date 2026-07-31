"""
Configurations of types of weapons and ships.

The create function is how new objects in the registry are instantiated.
"""
import importlib
import os
import pkgutil
from arena.engine.history import Tick
from arena.engine.objects.objectinspace import Point, Vector
from arena.engine.objects.ship import ShipType

# Force loading of every package under ois.registry so its subclasses can be found for the manual.
# Anchored to this file rather than to the working directory: a host picks that for itself, and
# scanning the wrong directory would leave the registry silently empty instead of failing.
_REGISTRY_DIR = os.path.dirname(os.path.abspath(__file__))

for (module_loader, name, ispkg) in pkgutil.iter_modules([_REGISTRY_DIR]):
    if name != 'builder':
        importlib.import_module(f'arena.engine.objects.registry.{name}')


def _subclasses_recursive(cls):
    direct = cls.__subclasses__()
    indirect = []
    for subclass in direct:
        indirect.extend(_subclasses_recursive(subclass))
    return direct + indirect


all_ship_types = {st.__name__: st() for st in _subclasses_recursive(ShipType)}


def spawn(type_name: str, name: str, vector: Vector, **kwargs):
    """Put a new object into space, facing and moving as the vector says.

    Only ship types are spawnable so far; this is where that widens."""
    type_instance = all_ship_types[type_name]
    return type_instance.base_type(name, type_instance, vector, **kwargs)


def create(name: str, type_name: str, position: tuple, **kwargs):
    """Spawn at a position, stationary and facing north. What game setup wants."""
    return spawn(type_name, name, Vector(Point(position[0], position[1]), heading=0, speed=0), **kwargs)


def from_plan(record: dict, tick: Tick):
    """Build what a line of a spawn plan describes, due at the given tick.

    `x`, `y`, `heading` and `speed` place it; `player` and `faction` are optional."""
    vector = Vector(Point(record.get('x', 0), record.get('y', 0)),
                    heading=record.get('heading', 0), speed=record.get('speed', 0))
    ois = spawn(record['type'], record['name'], vector, tick=tick, player=record.get('player', ''))
    ois.faction = record.get('faction')
    return ois


