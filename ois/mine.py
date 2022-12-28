import logging
from .objectinspace import ObjectInSpace
from .event import InternalEvent
from comp.warhead import SplinterWarhead
from ois.machineinspace import MachineType, MachineInSpace

logger = logging.getLogger(__name__)


class Mine(MachineInSpace):
    slow_down_rate = 5
    energy_per_tick = 1
    """Explody thing that does not appreciate when things get near it."""

    # ---------------------------------------------------------------------- QUERIES

    @property
    def is_destroyed(self) -> bool:
        return (self.hull <= 0) or (self.battery <= 0)

    @property
    def warhead(self):
        return self.weapons['warhead']

    # ---------------------------------------------------------------------- COMMANDS

    def take_damage_from(self, hitevent):
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
        self.warhead.post_move(objects_in_space)
        speed = self.speed - self.slow_down_rate
        self.vector.length = speed if speed > 0 else 0

        # Die when battery is dead.
        self.battery -= self.energy_per_tick
        if self.is_destroyed and (self.battery <= 0):
            self.owner.add_event(InternalEvent(f"{self.name} fizzled out."))


class SplinterMine(MachineType):
    """The basic mine"""
    base_type = Mine
    max_battery = 50
    start_battery = 50
    max_hull = 1

    @property
    def max_scan_distance(self):
        return self.weapons[0].range

    @property
    def weapons(self):
        return [
            SplinterWarhead('warhead'),
        ]
