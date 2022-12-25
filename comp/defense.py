from collections import namedtuple
from comp.component import Component
from ois.objectinspace import Point
from ois.event import HitEvent, InternalEvent

Quadrants = namedtuple('Quadrants', 'north east south west')
Section = namedtuple('Section', 'strength energy')


class Shields(Component):
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

    def quadrant_of(self, source_location: tuple) -> str:
        heading = self.container.heading_to(Point(*source_location))
        for angles, name in self.quadrants.items():
            if (angles[0] > angles[1]) and (heading >= angles[0]) or (heading <= angles[1]):
                # North
                return name
            elif angles[0] <= heading <= angles[1]:
                return name
        assert False, f"No quadrant found {source_location}, {heading}"

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
        self.strengths[shield_quadrant] -= hit_event.amount
        # Half point per shield point hit
        hit_event.score += (old_strength - self.strengths[shield_quadrant]) // 2
        if self.strengths[shield_quadrant] < 0:
            # 25 extra points for a shield break
            hit_event.score += 25
            breakthrough_damage = -self.strengths[shield_quadrant]
            self.add_internal_event(f"Hit on shield {shield_quadrant} broke the shield: {breakthrough_damage} passed through.")
            self.strengths[shield_quadrant] = 0
            return breakthrough_damage
        else:
            self.add_internal_event(f"Shield {shield_quadrant} hit for {hit_event.amount}. Remaining strength: {self.strengths[shield_quadrant]}")
        return 0

    # ---------------------------------------------------------------------- ENGINE HANDLERS

    def round_reset(self):
        for qdrt in ['N', 'E', 'S', 'W']:
            if self.strengths[qdrt] > self.max_strengths[qdrt]:
                self.add_internal_event(f"Shield {qdrt} boost dissipated.")
                self.strengths[qdrt] = self.max_strengths[qdrt]

