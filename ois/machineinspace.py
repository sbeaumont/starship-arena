from ois.objectinspace import ObjectInSpace
from comp.component import Component
from abc import ABCMeta


class MachineType(metaclass=ABCMeta):
    base_type = None
    max_hull = 0
    start_battery = 0

    @property
    def name(self):
        return self.__class__.__name__

    def create(self, name: str, pos: tuple, owner=None, heading: int = 0, speed: int = 0, tick: int = 0):
        assert self.base_type, f"{self.__class__.__name__} does not have a base_type defined"
        return self.base_type(name, self, pos, owner=owner, heading=heading, speed=speed, tick=tick)

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
    def __init__(self, name: str, _type: MachineType, xy: tuple, owner=None, heading=0, speed=0, tick=0):
        assert isinstance(_type, MachineType), f"{_type} is not an instance of MachineType"
        super().__init__(name, xy, heading, speed, tick=tick)
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
