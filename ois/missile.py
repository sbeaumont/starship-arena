import logging
from ois.objectinspace import ObjectInSpace, translate
from ois.machineinspace import MachineInSpace, MachineType
from ois.event import InternalEvent
from comp.warhead import RocketWarhead, SplinterWarhead

logger = logging.getLogger(__name__)


class Missile(MachineInSpace):
    """Flying thing that explodes when near its target."""
    energy_per_move: int = 5

    def __init__(self, name: str, _type, xy: tuple, owner: ObjectInSpace, heading: int = 0, speed=0, tick: int = 0):
        super().__init__(name, _type, xy, owner=owner, heading=heading, speed=_type.max_speed, tick=tick)
        self.target = None

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

    def post_move(self, objects_in_space):
        self.warhead.post_move(objects_in_space)
        if not self.is_destroyed:
            self._intercept()

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
        for ois in [o for o in objects_in_space.values() if (o != self) and (o.owner != self.owner)]:
            if self.can_scan(ois) and self.in_scan_cone(ois):
                if self.target:
                    if self.distance_to(ois.xy) < self.distance_to(self.target.xy):
                        self.target = ois
                else:
                    self.target = ois

    def _intercept(self):
        if self.target:
            intercept_pos = translate(self.target.xy, self.target.heading, self.target.speed)
            intercept_distance = self.distance_to(intercept_pos)
            if intercept_distance < self._type.max_speed:
                self.speed = round(intercept_distance, 0)
            self.heading = self.heading_to(intercept_pos)


class MissileType(MachineType):
    base_type = Missile


class Rocket(MissileType):
    """Dumb rocket"""
    base_type = Missile
    max_speed = 60
    explode_distance = 20
    explode_damage = 50
    max_battery = 75
    start_battery = 75
    max_hull = 1
    scan_cone = 0
    max_scan_distance = 20

    @property
    def weapons(self):
        return [
            RocketWarhead('warhead'),
        ]


class Splinter(MissileType):
    """The basic guided missile"""
    base_type = GuidedMissile
    max_speed = 60
    explode_distance = 6
    explode_damage = 75
    max_battery = 75
    start_battery = 75
    max_hull = 1
    scan_cone = 45
    max_scan_distance = 150

    @property
    def weapons(self):
        return [
            SplinterWarhead('warhead'),
        ]
