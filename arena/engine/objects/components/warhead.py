from dataclasses import dataclass
from enum import Enum, auto

from arena.engine.history import Tick
from arena.engine.world import World
from arena.engine.objects.component import Component
from arena.engine.objects.event import DamageType, ExplosionEvent, HitEvent
from arena.engine.objects.objectinspace import Encounter, Stance


class DamageFalloff(Enum):
    """How a warhead's damage thins out with distance."""
    Linear = auto()
    Flat = auto()


@dataclass
class Trigger(Encounter):
    """A warhead reaching what it goes off on."""
    warhead: 'Warhead' = None

    @property
    def subject(self):
        return self.warhead.container

    def act(self, world: World):
        self.warhead.explode(world, self.fraction)


class Warhead(Component):
    """Component that goes BOOM. Centralizes explode code into one component, like for missiles and mines."""

    def __init__(self, name: str, container=None):
        super().__init__(name, container)
        self.spent = False

    @property
    def status(self) -> dict:
        return {
            'Strength': self.damage,
            'Payload': self.name
        }

    def decide(self, world: World, tick: Tick):
        if self.container.is_destroyed and not self.spent:
            # Whatever killed it set it off, which is what makes one blast carry to the next.
            self.explode(world, self.container.tick_fraction)

    def encounter(self, world: World) -> Trigger | None:
        """Where in the tick it passes closest to something worth going off on.

        The earliest wins, so which object happens to be checked first cannot change where it
        goes off."""
        if self.spent:
            return None
        fractions = list()
        for ois in [o for o in world.objects.values() if self.triggers_on(o)]:
            from_fraction = max(self.container.tick_fraction, ois.tick_fraction)
            span = 1 - from_fraction
            closest = self.container.leg_from(from_fraction).closest_fraction(
                ois.leg_from(from_fraction), self.range)
            if closest is not None:
                fractions.append(from_fraction + closest * span)
        return Trigger(min(fractions), self) if fractions else None

    def triggers_on(self, ois) -> bool:
        """Anything hostile. Terrain is nobody's enemy, and is run into rather than set off on."""
        return ois.stance_towards(self.container) == Stance.Foe

    def explode(self, world, at_fraction: float = 1):
        """Go off, against everything where it was that far into the tick."""
        self.spent = True
        self.container.hull = 0
        # It goes no further than where it went off, and it does not go off twice.
        self.container.end_tick()

        # Generate the explosion: first all who can scan it see it.
        expl_event = ExplosionEvent(self.container.pos, self.damage_type, self.container, self.range)
        for ois in world.objects.values():
            if ois.distance_to(expl_event.pos) <= expl_event.modify_scan_range(ois._type.max_scan_distance):
                ois.add_event(expl_event)

        # The explosion generates hits on ALL in range
        hits = list()
        for ois in [ob for ob in world.objects.values() if ob != self.container]:
            distance = self.container.distance_to(ois.position_at(at_fraction))
            if distance <= self.range:
                damage = self._damage(distance)
                hit_event = HitEvent(self.container.pos, self.damage_type, self.container, ois, damage)
                ois.take_damage_from(hit_event)
                if ois.is_destroyed:
                    # Its leg ended here, so it goes no further than where the blast caught it.
                    ois.move(at_fraction)
                    ois.end_tick()
                self.owner.add_event(hit_event)
                hits.append(hit_event)

        # All who can observe the hits see it. Owner has already seen all, so filter out.
        # Urgh, double loop. Not elegant. No performance problems so far.
        for hit in hits:
            for ois in world.objects.values():
                if ois.distance_to(hit.pos) <= ois._type.max_scan_distance:
                    ois.add_event(hit)

    def _damage(self, distance: float):
        match self.falloff:
            case DamageFalloff.Flat:
                return self.damage
            case DamageFalloff.Linear:
                return self.damage - (distance if distance >= 0 else 0)


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

