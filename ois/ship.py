import logging
from typing import Protocol, runtime_checkable
from comp.defense import Shields
from comp.weapon import Laser, RocketLauncher
from ois.objectinspace import ObjectInSpace, Scan
from ois.rocket import Splinter
from rep.history import ShipSnapshot

logger = logging.getLogger(__name__)


@runtime_checkable
class Replenisher(Protocol):
    def replenish(self, ship):
        ...


class Ship(ObjectInSpace):
    """A player-commanded space ship."""
    def __init__(self, name: str, shiptype, xy: tuple, heading=0, speed=0):
        super().__init__(name, xy, heading, speed)
        self.owner = self
        self._type = shiptype
        self.generators = self._type.generators
        self.hull = self._type.max_hull
        self.defense = shiptype.defense
        for defense in self.defense:
            defense.attach(self)

        self.weapons = shiptype.weapons
        for weapon in self.weapons.values():
            weapon.attach(self)

        self.battery = shiptype.start_battery
        self.scans = dict()
        self.commands = None

    # ---------------------------------------------------------------------- QUERIES

    @property
    def is_destroyed(self) -> bool:
        return self.hull <= 0

    # ---------------------------------------------------------------------- COMMANDS

    def accelerate(self, delta_v):
        old_speed = self.speed
        if abs(delta_v) > self._type.max_delta_v:
            self.add_event(f"Limiting acceleration {delta_v} to max acceleration |{self._type.max_delta_v}|")
            delta_v = self._type.max_delta_v if delta_v > 0 else -self._type.max_delta_v
        self.speed += delta_v
        if self.speed > self._type.max_speed:
            self.speed = self._type.max_speed
            self.add_event(f"Limiting speed to max speed |{self._type.max_speed}|")
        if self.speed < -self._type.max_speed:
            self.speed = -self._type.max_speed
            self.add_event(f"Limiting speed to max speed |{-self._type.max_speed}|")
        if old_speed != self.speed:
            self.add_event(f"Changed speed from {old_speed} to {self.speed}")

    def fire(self, weapon_name: str, target_or_direction):
        if weapon_name in self.weapons:
            return self.weapons[weapon_name].fire(target_or_direction)
        else:
            self.add_event(f"No weapon named {weapon_name} found")

    def generate(self):
        self.battery += self.generators
        if self.battery > self._type.max_battery:
            self.battery = self._type.max_battery
        self.add_event(f"Generators generated {self.generators} energy: battery at {self.battery}/{self._type.max_battery}")

    def try_replenish(self, objects_in_space: dict):
        for replenisher in [ois for ois in objects_in_space.values() if isinstance(ois, Replenisher)]:
            replenisher.replenish(self)
            return
        self.add_event("Failed to replenish.")

    def turn(self, angle):
        if (self.speed > 0) and (abs(angle) > self._type.max_turn):
            self.add_event(f"Limiting turn {angle} to max turn |{self._type.max_turn}|")
            angle = self._type.max_turn if (angle > 0) else -self._type.max_turn
        self.heading = (self.heading + angle) % 360
        if angle != 0:
            self.add_event(f"Turned {angle} to {self.heading}")

    def scan(self, objects_in_space: dict):
        self.scans = dict()
        for ois in objects_in_space.values():
            if (ois != self) and self.distance_to(ois.xy) < self._type.max_scan_distance:
                scan = Scan.create_scan(self, ois)
                self.scans[ois.name] = scan
                self.add_event(f"Scanned {scan.name} at {scan.pos}, distance {scan.distance}, direction {scan.direction}, heading {scan.heading}")

    def take_damage_from(self, source_event, source_location, amount):
        """First pass the damage to the defense components, any remaining damage goes to the hull."""
        self.add_event(source_event)
        if hasattr(self, 'defense'):
            for d in self.defense:
                amount = d.take_damage_from(source_location, amount)
                if amount <= 0:
                    break
        if amount > 0:
            self.hull -= amount
            self.add_event(f"Hull decreased by {amount} to {self.hull}")

    # ---------------------------------------------------------------------- TIMED HANDLERS

    def post_move(self, objects_in_space):
        # Spend energy based on speed
        self.battery -= self.speed // 10

    def round_reset(self):
        super().round_reset()
        self.scans = dict()
        self.commands = None


class ShipType(object):
    base_type = Ship
    snapshot_type = ShipSnapshot


class H2545(ShipType):
    max_speed = 45
    max_turn = 35
    max_delta_v = 30
    max_hull = 100
    start_battery = 125
    generators = 8
    max_battery = 500
    max_scan_distance = 30

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 150, 'E': 100, 'S': 130, 'W': 100}),
        ]

    @property
    def weapons(self):
        return {
            'L1': Laser('L1'),
            'M1': RocketLauncher('M1', Splinter()),
            'M2': RocketLauncher('M2', Splinter())
        }


class H2552(ShipType):
    max_speed = 40
    max_turn = 35
    max_delta_v = 24
    max_hull = 110
    start_battery = 100
    generators = 7
    max_battery = 500
    max_scan_distance = 35

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 150, 'E': 130, 'S': 140, 'W': 130}),
        ]

    @property
    def weapons(self):
        return {
            'L1': Beam('L1'),
            'M1': RocketLauncher('M1', Splinter())
        }
