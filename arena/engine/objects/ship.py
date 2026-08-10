"""
The core game object, player controlled Ship!

- Has all the features to act on a player's Commands
- Stores a bunch of events in its history for reporting

This file also has command parameters that are specific to a ship (not a component) like acceleration and turning.
"""

import re
import logging
from abc import ABC
from typing import Protocol, runtime_checkable, NewType


from arena.engine.parameter import Parameter
from .machineinspace import MachineInSpace, MachineType
from .objectinspace import Impulse, ObjectInSpace, Vector
from arena.engine.objects.event import (DamageType, Effect, HitEvent, InternalEvent, Outcome,
                                        ScanEvent)
from arena.engine.history import Tick, TICK_ZERO
from arena.engine.world import World

logger = logging.getLogger(__name__)


@runtime_checkable
class Replenisher(Protocol):
    def replenish(self, ship):
        ...


shipType = NewType("ShipType", MachineType)

# What a machine calls the two things of its own that a blow can reach, once the defence
# components have had their turn. Symbols, so an interface can put words to them.
HULL = 'hull'
BATTERY = 'battery'


class Ship(MachineInSpace):
    """A player-commanded space ship."""

    kill_score = 100

    def __init__(self, name: str, _type: shipType, vector: Vector, owner = None,
                 tick: Tick = TICK_ZERO, player: str = ''):
        assert isinstance(vector, Vector)
        super().__init__(name, _type, vector, owner=self, tick=tick)
        self.generators = _type.generators
        self.score = 0
        self.commands = None
        self.player = player

    # ---------------------------------------------------------------------- QUERIES

    @property
    def category_name(self) -> str:
        return 'Ship'

    @property
    def is_player_controlled(self):
        return bool(self.player)

    @property
    def is_destroyed(self) -> bool:
        return self.hull <= 0

    @property
    def scans(self):
        return self.history.current.scans

    def scans_sorted_by(self, attribute_name):
        return self.history.current.scans_sorted_by(attribute_name)

    def can_scan(self, ois: ObjectInSpace):
        scan_distance = ois.modify_scan_range(self._type.max_scan_distance)
        return (ois != self) and self.distance_to(ois.xy) < scan_distance

    def modify_scan_range(self, scan_range: float) -> float:
        """How far a scanner has to reach for this ship: how big it is, then what it hides behind.

        Size first, because a cloak halves whatever there was to see."""
        scan_range = super().modify_scan_range(scan_range)
        for e in self.ecm.values():
            scan_range = e.modify_scan_range(scan_range)
        return round(scan_range, 1)

    # ---------------------------------------------------------------------- COMMANDS

    def accelerate(self, delta_v):
        old_speed = self.speed
        if abs(delta_v) > self._type.max_delta_v:
            self.add_internal_event(f"Limiting acceleration {delta_v} to max acceleration |{self._type.max_delta_v}|")
            delta_v = self._type.max_delta_v if delta_v > 0 else -self._type.max_delta_v
        self.vector = self.vector.accelerate(delta_v)
        if self.speed > self._type.max_speed:
            self.speed = self._type.max_speed
            self.add_internal_event(f"Limiting speed to max speed |{self._type.max_speed}|")
        if self.speed < -self._type.max_speed:
            self.vector.speed = -self._type.max_speed
            self.add_internal_event(f"Limiting speed to max speed |{-self._type.max_speed}|")
        if old_speed != self.speed:
            self.add_internal_event(f"Changed speed from {old_speed} to {self.speed}")

    def try_replenish(self, world: World):
        for replenisher in [ois for ois in world.objects.values() if isinstance(ois, Replenisher)]:
            replenisher.replenish(self)
            return
        self.add_internal_event("Failed to replenish.")

    def turn(self, angle):
        if abs(angle) > self._type.max_turn:
            self.add_event(InternalEvent(f"Limiting turn {angle} to max turn |{self._type.max_turn}|"))
            angle = self._type.max_turn if (angle > 0) else -self._type.max_turn
        self.vector.heading = (self.heading + angle) % 360
        if angle != 0:
            self.add_internal_event(f"Turned {angle} degrees to {self.heading}")

    # ---------------------------------------------------------------------- ENGINE HOOKS

    def generate(self):
        self.battery += self.generators
        if self.battery > self._type.max_battery:
            self.battery = self._type.max_battery
        self.add_internal_event(f"Generated {self.generators} energy: battery at {self.battery}/{self._type.max_battery}")

    def scan(self, world: World):
        for ois in [ob for ob in world.objects.values() if self.can_scan(ob)]:
            self.add_event(ScanEvent.create_scan(self, ois))

    def take_impulse_from(self, impulse: Impulse):
        """Bounce off it, and pay for the arrival in hull.

        Heading here is the direction of travel, so a bounce turns the ship with no regard for
        max_turn. Nobody ordered the turn, and coming out of it pointing somewhere else is most
        of what hitting a rock costs."""
        arrival = -self.vector.component_along(impulse.direction)
        # Damage first: a shield quadrant is read off the heading, and the bounce is about to
        # change it. What hit the bow struck the bow, however the ship ends up pointing.
        self.take_damage_from(HitEvent(self.pos, DamageType.Impact, impulse.source, self,
                                       self.mass * arrival))
        dx, dy = self.vector.delta
        mx, my = impulse.momentum
        self.vector = self.vector.with_delta(dx + mx / self.mass, dy + my / self.mass)
        self.add_internal_event(f"Struck {impulse.source.name} at {round(arrival)}: "
                                f"heading {self.heading} at {self.speed}")

    def _damage_hull(self, amount: int) -> int:
        """Take the damage, and score for the hull that was actually there to remove.

        Ships are cleared out at the end of the tick, so a later explosion in the same tick
        still lands on a corpse whose hull has gone negative. That scores nothing.
        """
        score = min(amount, self.hull) if self.hull > 0 else 0
        self.hull -= amount
        return score

    def take_damage_from(self, hit_event: HitEvent):
        """First pass the damage to the defense components, any remaining damage goes to the hull.

        A ship destroyed earlier in the same tick is still here to be hit, because the round
        clears the dead out only at the end of it. Only the first killing blow scores."""
        logger.debug(f"{self.name} taking damage from HitEvent {str(hit_event)}")
        self.add_event(hit_event)

        already_killed = self.is_destroyed

        # Inwards along the defence components, each one answering for itself and handing on
        # whatever it could not hold. The machine is the last layer, and answers the same way.
        amount = hit_event.amount
        for d in self.defense:
            effect = d.take_damage_from(hit_event._type, amount, hit_event.source.pos)
            hit_event.add_effect(effect)
            amount = effect.passed_on
            if amount <= 0:
                break

        if amount > 0:
            if hit_event._type == DamageType.Nanocyte:
                amount = 2 * amount
                score = self._damage_hull(amount)
                self.add_internal_event(f"Nanocytes burned your hull for {amount} to {self.hull}")
            elif hit_event._type == DamageType.EMP:
                battery_drain = amount if amount <= self.battery else self.battery
                score = min(amount, self.battery) // 2
                self.battery -= battery_drain
                self.add_internal_event(f"EMP blast drained out battery by {battery_drain}: {self.battery} left.")
            else:
                score = self._damage_hull(amount)
                self.add_internal_event(f"Hull decreased by {amount} to {self.hull}")

            what_was_hit = BATTERY if hit_event._type == DamageType.EMP else HULL
            hit_event.add_effect(Effect(what_was_hit, Outcome.Damaged, amount, score, 0))

        if not already_killed and self.is_destroyed:
            # Only the final blow scores the kill.
            hit_event.add_effect(Effect(HULL, Outcome.Breached, 0, self.kill_score, 0))
            self.add_internal_event(f"You were destroyed. Killing blow by {hit_event.source.name}.")

    def tick(self, tick: Tick):
        super().tick(tick)
        logger.debug(f"{self.name} starting tick {tick}")
        for comp in self.all_components.values():
            comp.tick(tick)

    def use_energy(self):
        for comp in self.all_components.values():
            comp.use_energy()
        if self.battery < (self.speed // 10):
            new_max_speed = self.battery * 10
            self.add_internal_event(f"Not enough energy for current speed: slowing down to {new_max_speed}")
            self.speed = new_max_speed

    def post_move(self, world):
        # Spend energy based on speed
        movement_energy = self.speed // 10
        self.battery -= movement_energy
        self.add_internal_event(f"Used {movement_energy} energy for movement.")

    def decide(self, world: World, tick: Tick):
        for comp in self.control.values():
            comp.decide(world, tick)

    # ---------------------------------------------------------------------- HISTORY INTERFACE

    def round_reset(self):
        super().round_reset()
        for d in self.defense:
            d.round_reset()
        self.commands = None

    def post_round_reset(self):
        super().post_round_reset()
        for d in self.defense:
            d.post_round_reset()


class ShipType(MachineType):
    base_type = Ship
    leaves_a_wreck = True
    mass = 1
    category = 'Ship'

    max_speed = None
    max_turn = None
    max_delta_v = None

    generators = None
    max_battery = 500

    max_scan_distance = None


class ShipParameter(Parameter, ABC):
    def __init__(self, name, ship: Ship, value: str):
        assert isinstance(ship, Ship)
        super().__init__(name)
        self.ship: Ship = ship
        self.input(value)


class AccelerationParameter(ShipParameter):
    @property
    def kind(self) -> str:
        return 'number'

    @property
    def is_valid(self):
        assert self._input is not None
        self.feedback.clear()
        if re.match(r"-?[0-9]+", self._input):
            result = abs(self.value) <= self.ship._type.max_delta_v
            if not result:
                self.feedback.append(f"{self._input} is outside max acceleration.")
        else:
            self.feedback.append(f"{self._input} is not a valid number.")
            result = False
        return result

    @property
    def value(self):
        return int(self._input)


class TurnParameter(ShipParameter):
    @property
    def kind(self) -> str:
        return 'number'

    @property
    def is_valid(self):
        assert self._input is not None
        self.feedback.clear()
        if re.match(r"-?[0-9]+", self._input):
            if abs(self.value) > self.ship._type.max_turn:
                self.feedback.append(
                    f"{self._input} is outside max turn: limited to |{self.ship._type.max_turn}|.")
            result = True
        else:
            self.feedback.append(f"{self._input} is not a valid number.")
            result = False
        return result

    @property
    def value(self):
        return int(self._input)
