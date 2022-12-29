import logging
from .event import InternalEvent, HitEvent
from .machineinspace import MachineInSpace

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


