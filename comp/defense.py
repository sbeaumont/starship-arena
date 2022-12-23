from collections import namedtuple
from ois.objectinspace import Point
from ois.event import HitEvent, InternalEvent

Quadrants = namedtuple('Quadrants', 'north east south west')
Section = namedtuple('Section', 'strength energy')


class Shields(object):
    """An object that is attached to an owner (Ship) and can defend its owner."""
    quadrants = {(315, 45): 'N', (45, 135): 'E', (135, 225): 'S', (225, 315): 'W'}

    def __init__(self, name: str, strengths: dict):
        self.name = name
        self.owner = None
        self.strengths = strengths.copy()
        self.max_strengths = strengths.copy()
        self.quadrant_status = {'N': 'On', 'E': 'On', 'S': 'On', 'W': 'On'}

    @property
    def status(self):
        return self.strengths.copy()

    def boost(self, qdrt, amount):
        if amount > self.owner.battery:
            amount = self.owner.battery
        self.owner.battery -= amount
        self.owner.add_event(InternalEvent(f"Used {amount} energy: battery at {self.owner.battery}"))

        self.strengths[qdrt] += amount
        if self.strengths[qdrt] > 2 * self.max_strengths[qdrt]:
            self.owner.add_event(InternalEvent(f"Shield {qdrt} can't boost beyond twice the strength."))
            self.strengths[qdrt] = 2 * self.max_strengths[qdrt]
        self.owner.add_event(InternalEvent(f"Boosted shield quadrant {qdrt} to {self.strengths[qdrt]}"))

    def attach(self, owner):
        self.owner = owner

    def quadrant_of(self, source_location: tuple) -> str:
        heading = self.owner.heading_to(Point(*source_location))
        for angles, name in self.quadrants.items():
            if (angles[0] > angles[1]) and (heading >= angles[0]) or (heading <= angles[1]):
                # North
                return name
            elif angles[0] <= heading <= angles[1]:
                return name
        assert False, f"No quadrant found {source_location}, {heading}"

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
            self.owner.add_event(InternalEvent(f"Hit on shield {shield_quadrant} broke the shield: {breakthrough_damage} passed through."))
            self.strengths[shield_quadrant] = 0
            return breakthrough_damage
        else:
            self.owner.add_event(InternalEvent(f"Shield {shield_quadrant} hit for {hit_event.amount}. Remaining strength: {self.strengths[shield_quadrant]}"))
        return 0

    def tick(self, tick_nr):
        pass

    def round_reset(self):
        for qdrt in ['N', 'E', 'S', 'W']:
            if self.strengths[qdrt] > self.max_strengths[qdrt]:
                self.owner.add_event(InternalEvent(f"Shield {qdrt} boost dissipated."))
                self.strengths[qdrt] = self.max_strengths[qdrt]

