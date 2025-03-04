"""
Abstract base class for all "man-made" objects.

It introduces a component system with:
- hull, battery
- offense, defense and ecm components

MachineType is the type object of a MachineInSpace, with the MachineInSpace - MachineType relationship being
similar to a object - class relationship. This was done to prevent an enormous class hierarchy and duplication.

Whenever a MachineInSpace needs type information it will query its type object (MachineType)

The variation lies in the components, and a MachineType simply defines a set of components. This could also
have been done with configuration files, but I made the choice that it's easier to just write the configuration
in Python and not have to parse and translate json files.

It also introduces an "owner" which is ultimately a player (but could also be an NPC object).
"""

from abc import ABCMeta
from .objectinspace import ObjectInSpace, Vector
from arena.engine.objects.component import Component
from arena.engine.history import Tick, TICK_ZERO


class MachineType(metaclass=ABCMeta):
    """Type Object for MachineInSpace objects."""

    base_type = None
    max_hull = 0
    start_battery = 0

    def create(self, name: str, vector: Vector, owner=None, tick: Tick = TICK_ZERO):
        assert self.base_type, f"{self.name} does not have a base_type defined"
        return self.base_type(name, self, vector, owner=owner, tick=tick)

    @property
    def type_name(self):
        return self.__class__.__name__

    @property
    def class_name(self):
        return None

    @property
    def name(self) -> str:
        if self.class_name:
            return f"{self.type_name} {self.class_name}"
        else:
            return self.type_name

    @property
    def weapons(self) -> list:
        return list()

    @property
    def defense(self) -> list:
        return list()

    @property
    def ecm(self) -> list:
        return list()


class MachineInSpace(ObjectInSpace, metaclass=ABCMeta):
    """A machine in space. Base class for all active objects like ships, bases, mines and missiles."""

    def __init__(self, name: str, _type: MachineType, vector: Vector, owner=None, tick: Tick = TICK_ZERO):
        assert isinstance(_type, MachineType), f"{_type} is not an instance of MachineType"
        assert isinstance(vector, Vector)
        super().__init__(name, vector, tick=tick)
        self._type: MachineType = _type
        self.hull: int = self._type.max_hull
        self.battery: int = self._type.start_battery
        self.owner = owner

        # Initialize components
        self.all_components: dict = dict()
        self.defense: list = self._type.defense
        self._attach_components(self.defense)
        self.weapons: dict = {comp.name: comp for comp in self._type.weapons}
        self._attach_components(self.weapons.values())
        self.ecm: dict = {comp.name: comp for comp in self._type.ecm}
        self._attach_components(self.ecm.values())

    def _attach_components(self, comps):
        for comp in comps:
            assert isinstance(comp, Component), f"{comp} is not a Component for {self._type}"
            self.all_components[comp.name] = comp
            comp.attach(self)

    @property
    def class_name(self):
        return self._type.name

    @property
    def type_name(self):
        return self._type.type_name

    @property
    def simple_snapshot(self):
        snap = super().simple_snapshot
        snap['hull'] = self.hull
        snap['battery'] = self.battery
        snap['class'] = self.class_name
        return snap

