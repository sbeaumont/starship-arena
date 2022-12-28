import logging
from typing import Protocol, runtime_checkable, NewType
from comp.defense import Shields
from comp.launcher import MissileLauncher
from comp.laser import Laser
from comp.ecm import Cloak
from ois.machineinspace import MachineInSpace, MachineType
from ois.objectinspace import ObjectInSpace
from ois.event import ScanEvent, InternalEvent, HitEvent
from ois.missile import Splinter, Rocket
from ois.mine import SplinterMine

logger = logging.getLogger(__name__)


@runtime_checkable
class Replenisher(Protocol):
    def replenish(self, ship):
        ...


shipType = NewType("ShipType", MachineType)


class Ship(MachineInSpace):
    """A player-commanded space ship."""
    def __init__(self, name: str, _type: shipType, xy: tuple, owner=None, heading=0, speed=0, tick=0):
        super().__init__(name, _type, xy, owner=self, heading=heading, speed=speed, tick=tick)
        self.generators = _type.generators
        self.score = 0
        self.commands = None

    # ---------------------------------------------------------------------- QUERIES

    @property
    def is_destroyed(self) -> bool:
        return self.hull <= 0

    @property
    def outer_defense(self):
        return self.defense[0] if len(self.defense) >= 1 else None

    @property
    def scans(self):
        return self.history.current.scans

    @property
    def snapshot(self):
        sn = super().snapshot
        sn['hull'] = self.hull
        sn['battery'] = self.battery
        sn['defense'] = self.defense.copy()
        return sn

    def can_scan(self, ois: ObjectInSpace):
        scan_distance = ois.modify_scan_range(self._type.max_scan_distance)
        return (ois != self) and self.distance_to(ois.xy) < scan_distance

    # ---------------------------------------------------------------------- COMMANDS

    def accelerate(self, delta_v):
        old_speed = self.speed
        if abs(delta_v) > self._type.max_delta_v:
            self.add_event(InternalEvent(f"Limiting acceleration {delta_v} to max acceleration |{self._type.max_delta_v}|"))
            delta_v = self._type.max_delta_v if delta_v > 0 else -self._type.max_delta_v
        self.speed += delta_v
        if self.speed > self._type.max_speed:
            self.speed = self._type.max_speed
            self.add_event(InternalEvent(f"Limiting speed to max speed |{self._type.max_speed}|"))
        if self.speed < -self._type.max_speed:
            self.speed = -self._type.max_speed
            self.add_event(InternalEvent(f"Limiting speed to max speed |{-self._type.max_speed}|"))
        if old_speed != self.speed:
            self.add_event(InternalEvent(f"Changed speed from {old_speed} to {self.speed}"))

    def fire(self, weapon_name: str, target_or_direction, objects_in_space=None):
        if weapon_name in self.weapons:
            return self.weapons[weapon_name].fire(target_or_direction, objects_in_space)
        else:
            self.add_event(InternalEvent(f"No weapon named {weapon_name} found"))

    def activation(self, name: str, on_off: bool):
        if name in self.all_components:
            self.all_components[name].activation(on_off)
        else:
            self.add_event(InternalEvent(f"Can not activate/deactivate unknown component: {name}"))

    def generate(self):
        self.battery += self.generators
        if self.battery > self._type.max_battery:
            self.battery = self._type.max_battery
        self.add_event(InternalEvent(f"Generators generated {self.generators} energy: battery at {self.battery}/{self._type.max_battery}"))

    def try_replenish(self, objects_in_space: dict):
        for replenisher in [ois for ois in objects_in_space.values() if isinstance(ois, Replenisher)]:
            replenisher.replenish(self)
            return
        self.add_event(InternalEvent("Failed to replenish."))

    def turn(self, angle):
        if (self.speed > 0) and (abs(angle) > self._type.max_turn):
            self.add_event(InternalEvent(f"Limiting turn {angle} to max turn |{self._type.max_turn}|"))
            angle = self._type.max_turn if (angle > 0) else -self._type.max_turn
        self.heading = (self.heading + angle) % 360
        if angle != 0:
            self.add_event(InternalEvent(f"Turned {angle} degrees to {self.heading}"))

    def scan(self, objects_in_space: dict):
        for ois in [ob for ob in objects_in_space.values() if self.can_scan(ob)]:
            self.add_event(ScanEvent.create_scan(self, ois))

    def modify_scan_range(self, scan_range: float) -> float:
        """Change a scanning object's scan range based on this ship's ECM."""
        for e in self.ecm.values():
            scan_range = e.modify_scan_range(scan_range)
        return round(scan_range, 1)

    def take_damage_from(self, hit_event: HitEvent):
        """First pass the damage to the defense components, any remaining damage goes to the hull.
        Note that we allow overkilling hits (and scoring) on the tick a ship is destroyed, but only
        count one killing blow for scoring."""
        self.add_event(hit_event)

        already_killed = self.is_destroyed

        amount = hit_event.amount
        if hasattr(self, 'outer_defense'):
            for d in self.defense:
                amount = d.take_damage_from(hit_event)
                if amount <= 0:
                    break
        if amount > 0:
            self.hull -= amount
            self.add_event(InternalEvent(f"Hull decreased by {amount} to {self.hull}"))
            # Score double points for hits on the hull
            score = 0
            if hit_event.can_score:
                score = amount * 2
                hit_event.score += score
            hit_event.notify_owner(f"{hit_event.source.name} hit {self.name}'s hull for {amount}: ({score} points)")

        if not already_killed and self.is_destroyed:
            # 100 points for an extra ship kill, but only for the final blow
            score = 0
            if hit_event.can_score:
                score = 100
                hit_event.score += 100
            hit_event.notify_owner(f"{hit_event.source.name} landed the killing blow on {self.name}: ({score} points)")
            self.add_event(InternalEvent(f"You were destroyed. Killing blow by {self.name}."))

    # ---------------------------------------------------------------------- TIMED HANDLERS

    def tick(self, tick_nr):
        for comp in self.all_components.values():
            comp.tick(tick_nr)

    def use_energy(self):
        for comp in self.all_components.values():
            comp.use_energy()
        if self.battery < (self.speed // 10):
            new_max_speed = self.battery * 10
            self.add_event(InternalEvent(f"Not enough energy for current speed: slowing down to {new_max_speed}"))
            self.speed = new_max_speed

    def post_move(self, objects_in_space):
        # Spend energy based on speed
        movement_energy = self.speed // 10
        self.battery -= movement_energy
        self.add_event(InternalEvent(f"Used {movement_energy} energy for movement."))

    def round_reset(self):
        super().round_reset()
        for d in self.defense:
            d.round_reset()
        self.commands = None


class ShipType(MachineType):
    base_type = Ship

    max_speed = None
    max_turn = None
    max_delta_v = None

    generators = None
    max_battery = 500

    max_scan_distance = None


class H2545(ShipType):
    max_speed = 45
    max_turn = 35
    max_delta_v = 25
    max_hull = 100
    start_battery = 125
    generators = 8
    max_scan_distance = 200

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 150, 'E': 100, 'S': 130, 'W': 100}),
        ]

    @property
    def weapons(self):
        return [
            Laser('L1', 180),
            MissileLauncher('S1', Splinter(), 4, (270, 90)),
            MissileLauncher('R1', Rocket(), 10),
            MissileLauncher('R2', Rocket(), 10),
            MissileLauncher('M1', SplinterMine(), 10, (135, 225))
        ]


class H2552(ShipType):
    max_speed = 40
    max_turn = 35
    max_delta_v = 20
    max_hull = 110
    start_battery = 100
    generators = 7
    max_scan_distance = 250

    @property
    def weapons(self):
        return [
            Laser('L1', 180, (270, 90)),
            MissileLauncher('S1', Splinter(), 10, (90, 270)),
            MissileLauncher('R1', Rocket(), 15)
        ]

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 150, 'E': 130, 'S': 140, 'W': 130}),
        ]

    @property
    def ecm(self):
        return [
            Cloak('C1', 0.2),
        ]


all_ship_types = {
    'H2545': H2545(),
    'H2552': H2552()
}
