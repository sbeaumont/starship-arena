"""Base class for anything built: ships, starbases, missiles, mines.

A machine holds hull, battery and components, and asks its MachineType for anything about the
model. See docs/adr/0003-type-objects-for-machines.md."""

from abc import ABC
from .objectinspace import Encounter, Impulse, ObjectInSpace, Stance, Vector
from .event import DamageType, HitEvent
from arena.engine.objects.component import Component
from arena.engine.history import Tick, TICK_ZERO
from arena.engine.world import World


class MachineType(object):
    """Type Object for MachineInSpace objects."""
    base_type = None
    max_hull = 0
    start_battery = 0
    leaves_a_wreck = False
    mass = 0

    # How much of a scanner's reach this model is worth to whoever is looking, as a percentage.
    # A machine is a standard object; the loud ones say so. Same scale as BodyType.
    visibility = 100

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
        """The type's game name."""
        if self.class_name:
            return f"{self.type_name} {self.class_name}"
        else:
            return self.type_name

    @property
    def weapons(self) -> list:
        """All weapon components of the machine type."""
        return list()

    @property
    def defense(self) -> list:
        """All defense components of the machine type."""
        return list()

    @property
    def ecm(self) -> list:
        """All ecm components of the machine type."""
        return list()

    @property
    def control(self) -> list:
        """All control components of the machine type."""
        return list()


class MachineInSpace(ObjectInSpace, ABC):
# class MachineInSpace(ObjectInSpace):
    """A machine in space. Base class for all active objects like ships, bases, mines and missiles."""

    def __init__(self, name: str, _type: MachineType, vector: Vector, owner=None, tick: Tick = TICK_ZERO):
        assert isinstance(_type, MachineType), f"{_type} is not an instance of MachineType"
        assert isinstance(vector, Vector)
        super().__init__(name, vector, tick=tick)
        self.owner = owner
        self._type: MachineType = _type

        # Initialize components
        self.all_components: dict = dict()
        self.hull: int = self._type.max_hull
        self.battery: int = self._type.start_battery

        # Initialize components
        self.defense: list = _type.defense
        self._attach_components(self.defense)
        self.weapons: dict = {comp.name: comp for comp in self._type.weapons}
        self._attach_components(self.weapons.values())
        self.ecm = {comp.name: comp for comp in self._type.ecm}
        self._attach_components(self.ecm.values())
        self.control = {comp.name: comp for comp in self._type.control}
        self._attach_components(self.control.values())

    def _attach_components(self, comps):
        for comp in comps:
            assert isinstance(comp, Component), f"{comp} is a {type(comp)}, not a Component for {self._type}"
            self.all_components[comp.name] = comp
            comp.attach(self)


    @property
    def class_name(self):
        return self._type.name

    @property
    def type_name(self):
        return self._type.type_name

    @property
    def mass(self) -> float:
        return self._type.mass

    def take_impulse_from(self, impulse: Impulse):
        """Stop dead where it arrived, and wear the arrival.

        Whether that is survivable is a question for the hull, which is where a mine that drifts
        into something differs from a missile that flies into it."""
        arrival = -self.vector.component_along(impulse.direction)
        self.speed = 0
        self.take_damage_from(HitEvent(self.pos, DamageType.Impact, impulse.source, self,
                                       self.mass * arrival))

    def encounter(self, world: World) -> Encounter | None:
        """The earliest of what it runs into and what any of its components names."""
        if self.is_destroyed or self.tick_ended:
            return None
        found = [e for e in
                 [super().encounter(world)] + [c.encounter(world) for c in self.all_components.values()]
                 if e is not None]
        return min(found, key=lambda e: e.fraction) if found else None

    def stance_towards(self, other: ObjectInSpace) -> Stance:
        """Asked of the owner, because a machine fights for whoever owns it."""
        mine, theirs = self.owner.faction, other.owner.faction
        if not mine or not theirs:
            return Stance.Neutral
        return Stance.Friend if mine == theirs else Stance.Foe

    @property
    def range(self) -> int:
        """The furthest any of this machine's components acts into space."""
        return max((c.range for c in self.all_components.values()), default=0)

    @property
    def leaves_a_wreck(self) -> bool:
        return self._type.leaves_a_wreck

    @property
    def snapshot(self):
        snap = super().snapshot
        snap['hull'] = self.hull
        snap['battery'] = self.battery
        snap['class'] = self.class_name
        snap['components'] = {name: dict(c.status) for name, c in self.all_components.items()}
        return snap

