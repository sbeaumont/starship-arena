"""
Configurations of types of weapons and ships.

The create function is how new objects in the registry are instantiated.
"""
import importlib
import os
import pkgutil
from arena.engine.history import Tick
from arena.engine.objects.objectinspace import Point, Vector
from arena.engine.objects.body import BodyType
from arena.engine.objects.ship import ShipType
from arena.engine.objects.starbase import StarbaseType

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


def _models(root, *filed_elsewhere) -> dict:
    """Every model under root, ready to build from, keyed by type name.

    A family with a registry of its own is left out of its parent's, so a starbase is a starbase
    and never also a ship. That is what saves every caller from asking about base classes."""
    skip = {c for other in filed_elsewhere for c in [other, *_subclasses_recursive(other)]}
    return {t.__name__: t() for t in _subclasses_recursive(root) if t not in skip}


all_starbase_types = _models(StarbaseType)
all_ship_types = _models(ShipType, StarbaseType)
all_body_types = _models(BodyType)

# What a director fields, as against the terrain a game is played over. Both are models and both
# are spawned by name, but only one of them has a hull to describe or a player to fly it.
all_fielded_types = all_ship_types | all_starbase_types
all_types = all_fielded_types | all_body_types


def spawn(type_name: str, name: str, vector: Vector, **kwargs):
    """Put a new object into space, facing and moving as the vector says."""
    type_instance = all_types[type_name]
    return type_instance.base_type(name, type_instance, vector, **kwargs)


def create(name: str, type_name: str, position: tuple, heading: float = 0, **kwargs):
    """Spawn at a position and a facing, stationary. What game setup wants."""
    return spawn(type_name, name, Vector(Point(position[0], position[1]), heading=heading, speed=0),
                 **kwargs)


def from_plan(record: dict, tick: Tick):
    """Build what a line of a spawn plan describes, due at the given tick.

    `x`, `y`, `heading` and `speed` place it; `player` and `faction` are optional."""
    vector = Vector(Point(record.get('x', 0), record.get('y', 0)),
                    heading=record.get('heading', 0), speed=record.get('speed', 0))
    ois = spawn(record['type'], record['name'], vector, tick=tick, player=record.get('player', ''))
    ois.faction = record.get('faction')
    return ois


