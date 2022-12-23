import logging
from ois.objectinspace import ObjectInSpace, translate
from ois.event import ExplosionEvent, HitEvent, DrawType, InternalEvent

logger = logging.getLogger(__name__)


class Missile(ObjectInSpace):
    """Guided missile that locks on the nearest target and explodes when near."""
    energy_per_move: int = 5

    def __init__(self, name: str, missile_type, xy: tuple, owner: ObjectInSpace, heading: int = 0):
        super().__init__(name, xy, heading, missile_type.max_speed)
        self._type = missile_type
        self.hull = self._type.max_hull
        self.battery = self._type.max_battery
        self.target = None
        self.owner = owner

    # ---------------------------------------------------------------------- QUERIES

    @property
    def is_destroyed(self) -> bool:
        return (self.hull <= 0) or (self.battery <= 0)

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
        if self._can_explode(objects_in_space):
            self._explode(objects_in_space)
        else:
            self._intercept()

        # Die when battery is dead.
        self.battery -= self.energy_per_move
        if self.is_destroyed and (self.battery <= 0):
            self.owner.add_event(InternalEvent(f"{self.name} fizzled out."))

    def _intercept(self):
        """Rockets just fly straight"""
        pass

    def _can_explode(self, objects_in_space: dict) -> bool:
        """Explode if there is an object in range that is not itself or owned by the same owner"""
        for ois_name, ois in objects_in_space.items():
            ois_is_self = (ois is self) or (ois is self.owner) or (ois.owner is self.owner)
            ois_in_range = (self.distance_to(ois.xy) <= self._type.explode_distance)
            if not ois_is_self and ois_in_range:
                return True
        return False

    def _explode(self, objects_in_space):
        self.hull = 0

        # Generate the explosion: first all who can scan it see it.
        expl_event = ExplosionEvent(self.pos, 'Explosion', self, self._type.explode_distance)
        for ois in objects_in_space.values():
            if ois.distance_to(expl_event.pos) <= ois._type.max_scan_distance:
                ois.add_event(expl_event)

        # The explosion generates hits on ALL in range
        hits = list()
        for ois in [ob for ob in objects_in_space.values() if ob != self]:
            distance = self.distance_to(ois.xy)
            if distance <= self._type.explode_distance:
                damage = self._damage(ois)
                hit_event = HitEvent(self.pos, 'Explosion', self, ois, damage)
                ois.take_damage_from(hit_event)
                # Owner sees all hits. Note that double add is okay since events for a tick are a set, not a list.
                self.owner.add_event(hit_event)
                hits.append(hit_event)

        # All who can observe the hits see it. Owner has already seen all, so filter out.
        # Urgh, double loop. Not elegant. No performance problems so far.
        for hit in hits:
            for ois in objects_in_space.values():
                if ois.distance_to(hit.pos) <= ois._type.max_scan_distance:
                    ois.add_event(hit)

    def _damage(self, ois):
        return self._type.explode_damage


class GuidedMissile(Missile):
    # ---------------------------------------------------------------------- QUERIES

    def can_scan(self, ois: ObjectInSpace) -> bool:
        scan_distance = ois.modify_scan_range(self._type.max_scan_distance)
        return (ois != self) and self.distance_to(ois.xy) < scan_distance

    def in_scan_cone(self, ois: ObjectInSpace) -> bool:
        direction_to_target = self.direction_to(ois.xy)
        return -self._type.scan_cone <= direction_to_target <= self._type.scan_cone

    def _damage(self, ois):
        return round(self._type.explode_damage / (1 + self.distance_to(ois.xy)))

    # ---------------------------------------------------------------------- COMMANDS

    def scan(self, objects_in_space: dict):
        self.target = None
        for ois in [o for o in objects_in_space.values() if (o != self) and (o != self.owner)]:
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


class Rocket(object):
    """Dumb rocket"""
    name = 'Rocket'
    base_type = Missile
    max_speed = 60
    explode_distance = 20
    explode_damage = 50
    max_battery = 75
    max_hull = 1
    scan_cone = 0
    max_scan_distance = 0


class Splinter(object):
    """The basic guided missile"""
    name = 'Splinter'
    base_type = GuidedMissile
    max_speed = 60
    explode_distance = 6
    explode_damage = 75
    scan_cone = 45
    max_battery = 75
    max_hull = 1
    max_scan_distance = 150
