import logging
from collections import namedtuple
from typing import Protocol, runtime_checkable
from math import sin, cos, radians, sqrt, atan2, pi

from history import DrawableEvent

logger = logging.getLogger(__name__)

Point = namedtuple("Point", "x y")


# class Attachable(Protocol):
#     """Any weapon, defense, utility, etc. that can be attached to a ship."""
#     def attach(self, owner):
#         ...
#
#     def tick(self, owner):
#         ...
#
#     @property
#     def status(self):
#         ...


class Scan(object):
    """A single instance of one object scanning another."""
    def __init__(self, ois, distance, direction, heading):
        self.ois = ois
        self.name = ois.name
        self.pos = ois.pos
        self.distance = distance
        self.direction = direction
        self.heading = heading

    @classmethod
    def create_scan(cls, source, scanned):
        return cls(scanned,
                   round(source.distance_to(scanned.xy), 1),
                   round(source.direction_to(scanned.xy), 1),
                   round(source.heading_to(scanned.xy), 1))

    def __str__(self):
        return f"Scan({self.name}, {self.pos}, {self.distance}, {self.heading}, {self.direction})"


def translate(p: Point, heading, distance) -> Point:
    angle = radians(heading)
    new_x = p.x + (sin(angle) * distance)
    new_y = p.y + (cos(angle) * distance)
    return Point(new_x, new_y)


class ObjectInSpace(object):
    """Any object in space, which can be ships, rockets, starbases, black holes, etc."""
    def __init__(self, name: str, xy: tuple, heading: int = 0, speed: int = 0):
        super().__init__()
        assert isinstance(heading, int)
        self.name = name
        self.xy = Point(xy[0], xy[1])
        self.heading = heading
        self.speed = speed
        self.owner = None
        self.history = None

    # ---------------------------------------------------------------------- QUERIES

    @property
    def pos(self):
        return round(self.xy.x, 1), round(self.xy.y, 1)

    def distance_to(self, point: Point):
        return round(sqrt((self.xy.x - point.x)**2 + (self.xy.y - point.y)**2), 1)

    def heading_to(self, point: Point):
        return round((atan2(point.x - self.xy.x, point.y - self.xy.y) / pi * 180) % 360, 1)

    def direction_to(self, point: Point):
        return self.heading_to(point) - self.heading

    @property
    def is_destroyed(self) -> bool:
        return False

    # ---------------------------------------------------------------------- HISTORY INTERFACE

    def add_event(self, event):
        if self.history and event:
            self.history.add_event(event)

    def round_reset(self):
        self.history.reset()

    # ---------------------------------------------------------------------- COMMANDS

    def move(self):
        """Move along heading with speed to next coordinate."""
        old_pos = self.pos
        self.xy = translate(self.xy, self.heading, self.speed)
        logger.debug(f"{self.name} moving from {old_pos} to {self.pos} heading {self.heading}")
        if old_pos != self.pos:
            self.add_event(f"Moved from {old_pos} to {self.pos}")

    def post_move(self, objects_in_space: dict):
        pass

    def generate(self):
        pass

    def scan(self, objects_in_space):
        pass

    def take_damage_from(self, source_event, source_location, amount):
        pass


class Rocket(ObjectInSpace):
    """Guided missile that locks on the nearest target and explodes when near."""
    energy_per_move: int = 5

    def __init__(self, name: str, xy: tuple, rocket_type, owner, heading: int = 0):
        assert isinstance(owner, ObjectInSpace)
        assert isinstance(heading, int)
        super().__init__(name, xy, heading, rocket_type.max_speed)
        self.hull = rocket_type.hull
        self.battery = rocket_type.max_battery
        self.max_speed = rocket_type.max_speed
        self.explode_distance = rocket_type.explode_distance
        self.explode_damage = rocket_type.explode_damage
        self.max_scan_distance = rocket_type.max_scan_distance
        self.scan_cone = rocket_type.scan_cone

        self.target = None
        self.owner = owner

    @property
    def is_destroyed(self) -> bool:
        return self.hull <= 0

    def scan(self, objects_in_space: dict):
        self.target = None
        for ois in [o for o in objects_in_space.values() if (o != self) and (o != self.owner)]:
            distance_to_target = self.distance_to(ois.xy)
            direction_to_target = self.direction_to(ois.xy)
            if (distance_to_target <= self.max_scan_distance) and (-self.scan_cone <= direction_to_target <= self.scan_cone):
                self.target = ois

    def can_explode(self, objects_in_space: dict) -> bool:
        for ois_name, ois in objects_in_space.items():
            ois_is_self = (ois is self) or (ois is self.owner) or (ois.owner is self.owner)
            ois_in_range = (self.distance_to(ois.xy) <= self.explode_distance)
            if not ois_is_self and ois_in_range:
                return True
        return False

    def post_move(self, objects_in_space):
        if self.can_explode(objects_in_space):
            self.explode(objects_in_space)
        else:
            if self.target:
                intercept_pos = translate(self.target.xy, self.target.heading, self.target.speed)
                intercept_distance = self.distance_to(intercept_pos)
                if intercept_distance < self.max_speed:
                    self.speed = round(intercept_distance, 0)
                self.heading = self.heading_to(intercept_pos)

        # Die when battery is dead.
        self.battery -= self.energy_per_move
        if not self.is_destroyed and (self.battery <= 0):
            self.hull = 0
            msg = f"{self.name} fizzled out."
            self.owner.add_event(msg)
            logger.info(msg)

    def take_damage_from(self, source_event, source_location, amount):
        # Any damage will destroy a rocket
        self.hull = 0
        self.owner.add_event(f"{self.name} {source_event[0].lower() + source_event[1:]}")

    def explode(self, objects_in_space):
        self.hull = 0
        self.owner.add_event(DrawableEvent('Explosion', self.pos, f"{self.name} exploded"))
        for ois in objects_in_space.values():
            if (ois != self) and (self.distance_to(ois.xy) <= self.explode_distance):
                ois.add_event(DrawableEvent('Explosion', self.pos, f"{self.name} exploded"))
                ois.take_damage_from(f"Hit by {self.name} for {self.explode_damage}", self.pos, self.explode_damage)
                self.owner.add_event(f"{self.name} hit {ois.name} at {ois.pos} for {self.explode_damage}")
            elif (ois != self) and (ois != self.owner) and (self.distance_to(ois.xy) <= ois.max_scan_distance):
                # object wasn't hit, but it did see what happened
                ois.add_event(DrawableEvent('Explosion', self.pos, f"{self.name} exploded"))


class Ship(ObjectInSpace):
    """A player-commanded space ship."""
    def __init__(self, name: str, shiptype, xy: tuple, heading=0, speed=0):
        super().__init__(name, xy, heading, speed)
        self.owner = self
        self.max_delta_v = shiptype.max_delta_v
        self.max_speed = shiptype.max_speed
        self.max_turn = shiptype.max_turn
        self.generators = shiptype.generators
        self.max_battery = shiptype.max_battery
        self.max_hull = shiptype.hull
        self.max_scan_distance = shiptype.max_scan_distance

        self.hull = self.max_hull
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
        if abs(delta_v) > self.max_delta_v:
            self.add_event(f"Limiting acceleration {delta_v} to max acceleration |{self.max_delta_v}|")
            delta_v = self.max_delta_v if delta_v > 0 else -self.max_delta_v
        self.speed += delta_v
        if self.speed > self.max_speed:
            self.speed = self.max_speed
            self.add_event(f"Limiting speed to max speed |{self.max_speed}|")
        if self.speed < -self.max_speed:
            self.speed = -self.max_speed
            self.add_event(f"Limiting speed to max speed |{-self.max_speed}|")
        if old_speed != self.speed:
            self.add_event(f"Changed speed from {old_speed} to {self.speed}")

    def fire(self, weapon_name: str, target_or_direction):
        if weapon_name in self.weapons:
            return self.weapons[weapon_name].fire(target_or_direction)
        else:
            self.add_event(f"No weapon named {weapon_name} found")

    def generate(self):
        self.battery += self.generators
        if self.battery > self.max_battery:
            self.battery = self.max_battery
        self.add_event(f"Generators generated {self.generators} energy: battery at {self.battery}/{self.max_battery}")

    def replenish(self, objects_in_space):
        for starbase in [ois for ois in objects_in_space.values() if isinstance(ois, Starbase)]:
            if (self.distance_to(starbase.xy) <= starbase.max_replenish_distance) and (self.speed <= starbase.max_replenish_speed):
                starbase.replenish(self)
                return
        self.add_event("Failed to replenish.")

    def turn(self, angle):
        if (self.speed > 0) and (abs(angle) > self.max_turn):
            self.add_event(f"Limiting turn {angle} to max turn |{self.max_turn}|")
            angle = self.max_turn if (angle > 0) else -self.max_turn
        self.heading = (self.heading + angle) % 360
        if angle != 0:
            self.add_event(f"Turned {angle} to {self.heading}")

    def scan(self, objects_in_space: dict):
        self.scans = dict()
        for ois in objects_in_space.values():
            if (ois != self) and self.distance_to(ois.xy) < self.max_scan_distance:
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


class Starbase(Ship):
    def __init__(self, name: str, shiptype, xy: tuple, heading=0, speed=0):
        super().__init__(name, shiptype, xy, heading, speed)
        self.max_replenish_distance = shiptype.max_replenish_distance
        self.max_replenish_speed = shiptype.max_replenish_speed

    def turn(self, angle):
        """Starbases don't turn. Nice try."""
        pass

    def accelerate(self, delta_v):
        """Starbases don't accelerate. Nice try."""
        pass

    def move(self):
        """Starbases do not move."""
        pass

    def replenish(self, ship):
        ship.hull = ship.max_hull
        ship.battery = ship.max_battery
        for weapon in ship.weapons.values():
            weapon.reset()
        self.add_event(f"Replenished {ship.name}")
        ship.add_event(f"Replenished by {self.name}")


