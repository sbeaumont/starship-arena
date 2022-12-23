from abc import ABC
from ois.event import InternalEvent


class Component(ABC):
    """An object that is attached to an owner (Ship) and can damage other objects in space."""
    def __init__(self, name: str, owner=None):
        self.name = name
        self.owner = owner

    @property
    def status(self) -> dict:
        """Returns a dictionary of names and values"""
        raise NotImplementedError

    def attach(self, owner):
        self.owner = owner

    def reset(self):
        pass

    def round_reset(self):
        pass

    def tick(self, tick_nr):
        pass

    def use_energy(self):
        pass

    def activation(self, on_off: bool):
        self.owner.add_event(InternalEvent(f"Component {self.name} can not be activated/deactivated."))
