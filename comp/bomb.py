from enum import Enum, auto
from comp.component import Component
from ois.event import ExplosionEvent, HitEvent


class DamageFalloff(Enum):
    Linear = auto()
    Flat = auto()


class BombType(object):
    name: str = 'Bomb'
    damage: int = 20
    range: int = 20
    falloff: DamageFalloff = DamageFalloff.Flat


class SplinterWarhead(BombType):
    name = 'Splinters'
    damage = 75
    range = 6
    falloff = DamageFalloff.Linear


class RocketWarhead(BombType):
    name = 'Nuclear'
    damage = 50
    range = 20
    falloff = DamageFalloff.Flat


class Bomb(Component):
    """Component that goes BOOM. Centralizes explode code into one component, like for missiles and mines."""
    def __init__(self, name: str, _type: BombType, container=None):
        super().__init__(name, container)
        self._type = _type

    @property
    def snapshot(self):
        return {
            'Strength': self._type.damage,
            'Payload': self._type.name
        }

    def post_move(self, objects_in_space):
        if self.can_explode(objects_in_space):
            self.explode(objects_in_space)

    def can_explode(self, objects_in_space: dict) -> bool:
        """Explode if there is an object in range that is not itself or owned by the same owner"""
        for ois_name, ois in objects_in_space.items():
            ois_in_range = (self.container.distance_to(ois.xy) <= self._type.range)
            if (ois.owner is not self.owner) and ois_in_range:
                return True
        return False

    def explode(self, objects_in_space):
        self.container.hull = 0

        # Generate the explosion: first all who can scan it see it.
        expl_event = ExplosionEvent(self.container.pos, 'Explosion', self.container, self._type.range)
        for ois in objects_in_space.values():
            if ois.distance_to(expl_event.pos) <= ois._type.max_scan_distance:
                ois.add_event(expl_event)

        # The explosion generates hits on ALL in range
        hits = list()
        for ois in [ob for ob in objects_in_space.values() if ob != self.container]:
            distance = self.container.distance_to(ois.xy)
            if distance <= self._type.range:
                damage = self._damage(ois)
                hit_event = HitEvent(self.container.pos, 'Explosion', self.container, ois, damage)
                ois.take_damage_from(hit_event)
                self.owner.add_event(hit_event)
                hits.append(hit_event)

        # All who can observe the hits see it. Owner has already seen all, so filter out.
        # Urgh, double loop. Not elegant. No performance problems so far.
        for hit in hits:
            for ois in objects_in_space.values():
                if ois.distance_to(hit.pos) <= ois._type.max_scan_distance:
                    ois.add_event(hit)

    def _damage(self, ois):
        match self._type.falloff:
            case DamageFalloff.Flat:
                return self._type.damage
            case DamageFalloff.Linear:
                dist = self.container.distance_to(ois.xy)
                return self._type.damage - (dist if dist >= 0 else 0)

