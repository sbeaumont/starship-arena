import logging
from .event import InternalEvent, HitEvent
from .machineinspace import MachineType, MachineInSpace
from comp.warhead import SplinterWarhead, NanocyteWarhead
from ois.objectinspace import Vector

logger = logging.getLogger(__name__)


class Mine(MachineInSpace):
    """Explody thing that does not appreciate when things get near it."""

    # ---------------------------------------------------------------------- QUERIES

    @property
    def is_destroyed(self) -> bool:
        return (self.hull <= 0) or (self.battery <= 0)

    @property
    def warhead(self):
        return self.weapons['warhead']

    # ---------------------------------------------------------------------- COMMANDS

    def take_damage_from(self, hitevent: HitEvent):
        # Any damage will destroy a mine
        if hitevent.amount > 0:
            self.hull = 0

    # ---------------------------------------------------------------------- HISTORY INTERFACE

    @property
    def snapshot(self):
        sn = super().snapshot
        sn['battery'] = self.battery
        sn['hull'] = self.hull
        return sn

    # ---------------------------------------------------------------------- ENGINE HOOKS

    def post_move(self, objects_in_space):
        for wh in self.weapons.values():
            wh.post_move(objects_in_space)

        speed = self.speed - self._type.slow_down_rate
        self.vector.speed = speed if speed > 0 else 0

        # Die when battery is dead.
        self.battery -= self._type.energy_per_tick
        if self.is_destroyed and (self.battery <= 0):
            self.owner.add_event(InternalEvent(f"{self.name} fizzled out."))


class MineType(MachineType):
    slow_down_rate = 5
    energy_per_tick = 1
    max_speed = 0

    def create(self, name: str, vector: Vector, owner=None, tick: int = 0):
        vector = vector.accelerate(-self.slow_down_rate)
        return super().create(name, vector, owner, tick)

    @property
    def max_scan_distance(self):
        return self.weapons[0].range


class SplinterMine(MineType):
    """The basic mine"""
    base_type = Mine
    max_battery = 50
    start_battery = 50
    max_hull = 1

    @property
    def weapons(self):
        return [
            SplinterWarhead('warhead'),
        ]


class NanocyteMine(MineType):
    """A mine that releases a cloud of nanocytes after exploding..."""
    base_type = Mine
    max_battery = 50
    start_battery = 50
    max_hull = 1

    @property
    def weapons(self):
        return [
            SplinterWarhead('warhead'),
            NanocyteWarhead('nanohead')
        ]
