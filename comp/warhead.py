from enum import Enum, auto
from comp.component import Component
from ois.event import ExplosionEvent, HitEvent


class DamageFalloff(Enum):
    Linear = auto()
    Flat = auto()


class DamageType(Enum):
    Explosion = 'Explosion'
    Nanocyte = 'Nanocyte'
    EMP = 'EMP'

    def __str__(self):
        return f"{self.value}"


class Warhead(Component):
    """Component that goes BOOM. Centralizes explode code into one component, like for missiles and mines."""
    @property
    def status(self) -> dict:
        return {
            'Strength': self.damage,
            'Payload': self.name
        }

    def post_move(self, objects_in_space):
        if self.can_explode(objects_in_space):
            self.explode(objects_in_space)

    def can_explode(self, objects_in_space: dict) -> bool:
        """Explode if there is an object in range that is not itself or owned by the same owner"""
        for ois_name, ois in objects_in_space.items():
            ois_in_range = (self.container.distance_to(ois.xy) <= self.range)
            if (ois.owner is not self.owner) and ois_in_range:
                return True
        return False

    def explode(self, objects_in_space):
        self.container.hull = 0

        # Generate the explosion: first all who can scan it see it.
        expl_event = ExplosionEvent(self.container.pos, self.damage_type, self.container, self.range)
        for ois in objects_in_space.values():
            if ois.distance_to(expl_event.pos) <= ois._type.max_scan_distance:
                ois.add_event(expl_event)

        # The explosion generates hits on ALL in range
        hits = list()
        for ois in [ob for ob in objects_in_space.values() if ob != self.container]:
            distance = self.container.distance_to(ois.xy)
            if distance <= self.range:
                damage = self._damage(ois)
                hit_event = HitEvent(self.container.pos, self.damage_type, self.container, ois, damage)
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
        match self.falloff:
            case DamageFalloff.Flat:
                return self.damage
            case DamageFalloff.Linear:
                dist = self.container.distance_to(ois.xy)
                return self.damage - (dist if dist >= 0 else 0)


class SplinterWarhead(Warhead):
    damage_type = DamageType.Explosion
    damage = 75
    range = 6
    falloff = DamageFalloff.Linear


class PowerSplinterWarhead(Warhead):
    damage_type = DamageType.Explosion
    damage = 100
    range = 6
    falloff = DamageFalloff.Linear


class RocketWarhead(Warhead):
    damage_type = DamageType.Explosion
    damage = 50
    range = 20
    falloff = DamageFalloff.Flat


class NanocyteWarhead(Warhead):
    damage_type = DamageType.Nanocyte
    damage = 100
    range = 50
    falloff = DamageFalloff.Linear


class EMPWarhead(Warhead):
    damage_type = DamageType.EMP
    damage = 100
    range = 10
    falloff = DamageFalloff.Linear

