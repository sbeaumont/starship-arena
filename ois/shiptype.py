"""
Configurations of types of weapons and ships
"""

from rep.history import History
from ois.ship import H2545
from ois.starbase import SB2531

type_classes = {
    'H2545': H2545,
    'SB2531': SB2531
}


def create(name: str, type_name: str, position: tuple, tick: int):
    """Return an instance of a ship type object by its class name."""
    type_instance = type_classes[type_name]()
    ois = type_instance.base_type(name, type_instance, position)
    ois.history = History(ois, type_instance.snapshot_type, tick)
    return ois


