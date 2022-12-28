from abc import ABC
from ois.event import InternalEvent


class Component(ABC):
    """An object that is attached to an owner (Ship) and can damage other objects in space."""
    def __init__(self, name: str, container=None):
        assert name, "name may not be None"
        self.name = name
        self.container = container

    @property
    def status(self) -> dict:
        """Returns a dictionary of names and values"""
        raise NotImplementedError

    @property
    def owner(self):
        return self.container.owner

    @property
    def description(self):
        return self.__class__.__name__

    def add_internal_event(self, message: str):
        self.owner.add_event(InternalEvent(message))

    def attach(self, container):
        self.container = container

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
