"""
Configurations of types of weapons and ships.

The create function is how new objects in the registry are instantiated.
"""
import importlib
import pkgutil
from ois.objectinspace import Point, Vector
from ois.ship import ShipType

# Force loading of every package under ois.registry so its subclasses can be found for the manual.
for (module_loader, name, ispkg) in pkgutil.iter_modules(['ois/registry', ]):
    if name != 'builder':
        importlib.import_module(f'ois.registry.{name}')


def _subclasses_recursive(cls):
    direct = cls.__subclasses__()
    indirect = []
    for subclass in direct:
        indirect.extend(_subclasses_recursive(subclass))
    return direct + indirect


all_ship_types = {st.__name__: st for st in _subclasses_recursive(ShipType)}


def create(name: str, type_name: str, position: tuple, **kwargs):
    """Return an instance of a ship type object by its class name."""
    type_instance = all_ship_types[type_name]()
    pos = Vector(Point(position[0], position[1]), heading=0, speed=0)
    return type_instance.base_type(name, type_instance, pos, **kwargs)


