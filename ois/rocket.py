import logging
from rep.history import RocketSnapshot
from ois.objectinspace import ObjectInSpace, translate

logger = logging.getLogger(__name__)


class Rocket(ObjectInSpace):
    """Guided missile that locks on the nearest target and explodes when near."""
    energy_per_move: int = 5

    def __init__(self, name: str, xy: tuple, rocket_type, owner, heading: int = 0):
        assert isinstance(owner, ObjectInSpace)
        assert isinstance(heading, int)
        super().__init__(name, xy, heading, rocket_type.max_speed)
        self._type = rocket_type
        self.hull = self._type.max_hull
        self.battery = self._type.max_battery
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
            if (distance_to_target <= self._type.max_scan_distance) and \
                    (-self._type.scan_cone <= direction_to_target <= self._type.scan_cone):
                self.target = ois

    def can_explode(self, objects_in_space: dict) -> bool:
        for ois_name, ois in objects_in_space.items():
            ois_is_self = (ois is self) or (ois is self.owner) or (ois.owner is self.owner)
            ois_in_range = (self.distance_to(ois.xy) <= self._type.explode_distance)
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
                if intercept_distance < self._type.max_speed:
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
        self.owner.add_drawable_event('Explosion', self.pos, f"{self.name} exploded")
        for ois in objects_in_space.values():
            distance = self.distance_to(ois.xy)
            if (ois != self) and (distance <= self._type.explode_distance):
                ois.add_drawable_event('Explosion', self.pos, f"{self.name} exploded")
                damage = round(self._type.explode_damage / (1 + distance))
                ois.take_damage_from(f"Hit by {self.name} for {damage}", self.pos, damage)
                self.owner.add_event(f"{self.name} hit {ois.name} at {ois.pos} for {damage}")
            elif (ois != self) and (ois != self.owner) and (distance <= ois._type.max_scan_distance):
                # object wasn't hit, but it did see what happened
                ois.add_drawable_event('Explosion', self.pos, f"{self.name} exploded")


class Splinter(object):
    """Default rocket"""
    base_type = Rocket
    snapshot_type = RocketSnapshot
    max_speed = 60
    explode_distance = 6
    explode_damage = 75
    scan_cone = 45
    max_battery = 75
    max_hull = 1
    max_scan_distance = 150
