"""
Configurations of types of weapons and ships
"""

from ois.ship import H2545, H2552
from ois.starbase import SB2531
from ois.objectinspace import Point, Vector

type_classes = {
    'H2545': H2545,
    'SB2531': SB2531,
    'H2552': H2552,
}


def create(name: str, type_name: str, position: tuple, **kwargs):
    """Return an instance of a ship type object by its class name."""
    type_instance = type_classes[type_name]()
    pos = Vector(Point(position[0], position[1]), heading=0, speed=0)
    return type_instance.base_type(name, type_instance, pos, **kwargs)


