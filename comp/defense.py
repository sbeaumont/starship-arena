from collections import namedtuple
from comp.component import Component
from ois.objectinspace import Point
from ois.event import HitEvent
from .warhead import DamageType

Quadrants = namedtuple('Quadrants', 'north east south west')
Section = namedtuple('Section', 'strength energy')


class Shields(Component):
    shield_break_score = 25

    """An object that is attached to an owner (Ship) and can defend its owner."""
    quadrants = {(315, 45): 'N', (45, 135): 'E', (135, 225): 'S', (225, 315): 'W'}

    def __init__(self, name: str, strengths: dict):
        super().__init__(name)
        self.strengths = strengths.copy()
        self.max_strengths = strengths.copy()
        # self.quadrant_status = {'N': 'On', 'E': 'On', 'S': 'On', 'W': 'On'}

    # ---------------------------------------------------------------------- QUERIES

    @property
    def status(self):
        return self.strengths.copy()

    @property
    def description(self):
        ms = [str(s) for s in self.max_strengths.values()]
        return f"Shield ({'/'.join(ms)})"

    def quadrant_of(self, source_location: Point) -> str:
        heading = self.container.heading_to(source_location)
        for angles, name in self.quadrants.items():
            if (angles[0] > angles[1]) and (heading >= angles[0]) or (heading <= angles[1]):
                # North
                return name
            elif angles[0] <= heading <= angles[1]:
                return name
        assert False, f"No quadrant found {source_location.as_tuple}, {heading}"

    # ---------------------------------------------------------------------- COMMANDS

    def boost(self, qdrt, amount):
        if amount > self.container.battery:
            amount = self.container.battery
        self.container.battery -= amount
        self.add_internal_event(f"Used {amount} energy: battery at {self.container.battery}")

        self.strengths[qdrt] += amount
        if self.strengths[qdrt] > 2 * self.max_strengths[qdrt]:
            self.add_internal_event(f"Shield {qdrt} can't boost beyond twice the strength.")
            self.strengths[qdrt] = 2 * self.max_strengths[qdrt]
        self.add_internal_event(f"Boosted shield quadrant {qdrt} to {self.strengths[qdrt]}")

    def take_damage_from(self, hit_event: HitEvent) -> int:
        """Absorb damage on shield quadrant, return any remaining damage."""
        shield_quadrant = self.quadrant_of(hit_event.source.pos)
        old_strength = self.strengths[shield_quadrant]

        # Nanocytes can not penetrate shields, but if there's no shield there, everything gets passed through... uh oh.
        if (hit_event._type == DamageType.Nanocyte):
            if old_strength > 0:
                hit_event.notify_owner(f"Nanocytes splashed harmlessly against {self.container.name}'s shield.")
                return 0
            else:
                return hit_event.amount

        self.strengths[shield_quadrant] -= hit_event.amount
        if old_strength >= hit_event.amount:
            shield_score = 0
            if hit_event.can_score:
                shield_score = (old_strength - self.strengths[shield_quadrant]) // 2
                hit_event.score += shield_score
            hit_event.notify_owner(f"{hit_event.source.name} hit {self.container.name}'s shield: ({shield_score} points).")
            self.add_internal_event(f"Shield {shield_quadrant} hit for {hit_event.amount}. Remaining strength: {self.strengths[shield_quadrant]}")
            return 0
        else:
            shield_score = 0
            if hit_event.can_score:
                shield_score = old_strength // 2
                hit_event.score += shield_score
            hit_event.notify_owner(f"{hit_event.source.name} hit {self.container.name}'s shield: ({shield_score} points).")
            if hit_event.can_score:
                hit_event.score += self.shield_break_score
                hit_event.notify_owner(f"{hit_event.source.name} broke {self.container.name}'s shield: ({self.shield_break_score} points).")
            breakthrough_damage = -self.strengths[shield_quadrant]
            self.strengths[shield_quadrant] = 0
            self.add_internal_event(f"Hit on shield {shield_quadrant} broke the shield: {breakthrough_damage} passed through.")
            return breakthrough_damage

    # ---------------------------------------------------------------------- ENGINE HANDLERS

    def round_reset(self):
        for qdrt in ['N', 'E', 'S', 'W']:
            if self.strengths[qdrt] > self.max_strengths[qdrt]:
                self.add_internal_event(f"Shield {qdrt} boost dissipated: now at {self.strengths[qdrt]}.")
                self.strengths[qdrt] = self.max_strengths[qdrt]

