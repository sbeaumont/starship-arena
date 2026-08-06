"""
Mines slow down and sit still in space. Go boom based on the warhead they have.
"""

import logging
from .event import InternalEvent, HitEvent
from .machineinspace import MachineInSpace
from ..history import Tick
from arena.engine.world import World

logger = logging.getLogger(__name__)


class Mine(MachineInSpace):
    """Explody thing that does not appreciate when things get near it."""

    # ---------------------------------------------------------------------- QUERIES

    @property
    def is_destroyed(self) -> bool:
        return (self.hull <= 0) or (self.battery <= 0)

    @property
    def category_name(self) -> str:
        return 'Mine'

    @property
    def warhead(self):
        return self.weapons['warhead']

    # ---------------------------------------------------------------------- COMMANDS

    def take_damage_from(self, hitevent: HitEvent):
        """Hull is what a mine can absorb, which is how it tells a drift from a collision."""
        self.hull -= hitevent.amount

    # ---------------------------------------------------------------------- HISTORY INTERFACE



    # ---------------------------------------------------------------------- ENGINE HOOKS

    def decide(self, world: World, tick: Tick):
        for wh in self.weapons.values():
            wh.decide(world, tick)

    def post_move(self, world):
        for wh in self.weapons.values():
            wh.post_move(world)

        speed = self.speed - self._type.slow_down_rate
        self.vector.speed = speed if speed > 0 else 0

        # Die when battery is dead.
        self.battery -= self._type.energy_per_tick
        if self.is_destroyed and (self.battery <= 0):
            self.owner.add_event(InternalEvent(f"{self.name} fizzled out."))


