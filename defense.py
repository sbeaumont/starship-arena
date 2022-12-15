from collections import namedtuple
from objectinspace import Point

Quadrants = namedtuple('Quadrants', 'north east south west')
Section = namedtuple('Section', 'strength energy')


class Shields(object):
    """An object that is attached to an owner (Ship) and can defend its owner."""
    quadrants = {(315, 45): 'N', (45, 135): 'E', (135, 225): 'S', (225, 315): 'W'}

    def __init__(self, name: str, strengths: dict):
        self.name = name
        self.owner = None
        self.strengths = strengths.copy()

    def attach(self, owner):
        self.owner = owner

    def quadrant_of(self, source_location: tuple) -> str:
        heading = self.owner.heading_to(Point(*source_location))
        for angles, name in self.quadrants.items():
            if (angles[0] > angles[1]) and (heading > angles[0]) or (heading <= angles[0]):
                # North
                return name
            elif angles[0] <= heading < angles[1]:
                return name
        assert False, f"No quadrant found {source_location}, {heading}"

    def take_damage_from(self, source_location: tuple, amount: int) -> int:
        """Absorb damage on shield quadrant, return any remaining damage."""
        shield_quadrant = self.quadrant_of(source_location)
        self.strengths[shield_quadrant] -= amount
        if self.strengths[shield_quadrant] < 0:
            breakthrough_damage = -self.strengths[shield_quadrant]
            self.owner.add_event(f"Hit on shield {shield_quadrant} broke the shield: {breakthrough_damage} passed through.")
            self.strengths[shield_quadrant] = 0
            return breakthrough_damage
        else:
            self.owner.add_event(f"Shield {shield_quadrant} hit for {amount}. Remaining strength: {self.strengths[shield_quadrant]}")
        return 0

    def tick(self, tick_nr):
        pass

    @property
    def status(self):
        return self.strengths.copy()