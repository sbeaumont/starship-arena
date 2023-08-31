from abc import ABCMeta
from .objectinspace import ObjectInSpace, Vector
from comp.component import Component


class MachineType(metaclass=ABCMeta):
    base_type = None
    max_hull = 0
    start_battery = 0

    def create(self, name: str, vector: Vector, owner=None, tick: int = 0):
        assert self.base_type, f"{self.name} does not have a base_type defined"
        return self.base_type(name, self, vector, owner=owner, tick=tick)

    @property
    def name(self) -> str:
        return self.__class__.__name__

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
    """A machine in space."""
    def __init__(self, name: str, _type: MachineType, vector: Vector, owner=None, tick=0):
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
    def type_name(self):
        return self._type.name

