"""
Missiles are not controlled by players and fly, track and explode based on their programming.

Missiles just fly straight, GuidedMissiles add features to track targets.
Further capabilities are defined by their warheads (and other components in future?).
"""

import logging
from dataclasses import replace

from .event import InternalEvent
from .objectinspace import ObjectInSpace, Vector
from .machineinspace import MachineInSpace, MachineType
from arena.engine.history import Tick, TICK_ZERO

logger = logging.getLogger(__name__)


class Missile(MachineInSpace):
    """Flying thing that explodes when near its target."""

    def __init__(self, name: str, _type, vector: Vector, owner: ObjectInSpace, tick: Tick = TICK_ZERO):
        super().__init__(name, _type, vector, owner=owner, tick=tick)
        self.target = None
        self.energy_per_move = _type.energy_per_move

    # ---------------------------------------------------------------------- QUERIES

    @property
    def is_destroyed(self) -> bool:
        return (self.hull <= 0) or (self.battery <= 0)

    @property
    def warhead(self):
        return self.weapons['warhead']

    # ---------------------------------------------------------------------- COMMANDS

    def take_damage_from(self, hitevent):
        # Any damage will destroy a rocket
        if hitevent.amount > 0:
            self.hull = 0

    # ---------------------------------------------------------------------- HISTORY INTERFACE

    @property
    def snapshot(self):
        sn = super().snapshot
        sn['hull'] = self.hull
        sn['battery'] = self.battery
        sn['target'] = self.target
        return sn

    # ---------------------------------------------------------------------- ENGINE HOOKS

    def decide(self, objects_in_space: dict):
        self.warhead.decide(objects_in_space)
        if not self.is_destroyed:
            self._intercept()

    def post_move(self, objects_in_space):
        # Die when battery is dead.
        self.battery -= self.energy_per_move
        if self.is_destroyed and (self.battery <= 0):
            self.owner.add_event(InternalEvent(f"{self.name} fizzled out."))

    def _intercept(self):
        """Rockets just fly straight"""
        pass


class GuidedMissile(Missile):
    """Guided version of the Missile. Has the ability to lock on and intercept its closest target."""

    # ---------------------------------------------------------------------- QUERIES

    def can_scan(self, ois: ObjectInSpace) -> bool:
        scan_distance = ois.modify_scan_range(self._type.max_scan_distance)
        return (ois != self) and self.distance_to(ois.xy) < scan_distance

    def in_scan_cone(self, ois: ObjectInSpace) -> bool:
        direction_to_target = self.direction_to(ois.xy)
        return -self._type.scan_cone <= direction_to_target <= self._type.scan_cone

    # ---------------------------------------------------------------------- COMMANDS

    def scan(self, objects_in_space: dict):
        self.target = None
        for ois in [o for o in objects_in_space.values() if (o != self) and (o.owner.faction != self.owner.faction)]:
            if self.can_scan(ois) and self.in_scan_cone(ois):
                if self.target:
                    if self.distance_to(ois.xy) < self.distance_to(self.target.xy):
                        self.target = ois
                else:
                    self.target = ois

    def _intercept(self):
        if self.target:
            intercept_pos = self.target.vector.translate(self.target.heading, self.target.speed).pos
            intercept_distance = self.distance_to(intercept_pos)
            if intercept_distance < self.speed:
                self.vector.speed = round(intercept_distance - 1, 0)
            target_dir = self.direction_to(intercept_pos)
            if target_dir < -self._type.max_turn:
                target_dir = -self._type.max_turn
            elif target_dir > self._type.max_turn:
                target_dir = self._type.max_turn
            self.vector.turn(target_dir)


class MissileType(MachineType):
    base_type = Missile
    energy_per_move: int = 5
    max_speed = 0
    max_turn = 45

    def create(self, name: str, vector: Vector, owner=None, tick: Tick = TICK_ZERO):
        vector = replace(vector, speed=self.max_speed)
        return super().create(name, vector, owner, tick)
