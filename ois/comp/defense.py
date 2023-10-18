from ois.comp.component import Component, ComponentParameter
from ois.objectinspace import Point
from ois.machineinspace import MachineInSpace
from ois.event import HitEvent
from .warhead import DamageType


class BoostQuadrantParameter(ComponentParameter):
    """Represents the two boost parameters (quadrant and amount) in one because they're so strongly related."""

    @property
    def number_of_inputs(self) -> int:
        return 2

    @property
    def is_valid(self):
        assert self._input is not None
        assert isinstance(self._input, list)
        self.feedback.clear()
        if len(self._input) != 2:
            self.feedback.append(f"Expected parameters (quadrant) (boost amount) but got {self._input}")
            return False
        quadrant, amount = self._input
        assert isinstance(amount, str)
        assert isinstance(quadrant, str)
        if quadrant not in ['N', 'E', 'S', 'W']:
            self.feedback.append(f"{quadrant} is not one of (N, E, S, W).")
            return False
        if not amount.isnumeric():
            self.feedback.append(f"{amount} is not a number.")
            return False
        if int(amount) > (2 * self.component.max_strength[quadrant]):
            self.feedback.append(f"Can not boost quadrant {quadrant} beyond twice its strength")
            return False
        return True


class Shields(Component):
    """Belongs in the defense components list, defends the ship from damage."""

    shield_break_score = 25

    quadrants = {(315, 45): 'N', (45, 135): 'E', (135, 225): 'S', (225, 315): 'W'}

    def __init__(self, name: str, strengths: dict, container: MachineInSpace=None):
        super().__init__(name, container)
        self.strengths = strengths.copy()
        self.max_strengths = strengths.copy()

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

    @property
    def expected_parameters(self):
        return [BoostQuadrantParameter('boost', self)]

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
        damage_amount = hit_event.amount

        if old_strength == 0:
            # Shield is down, just pass through the damage.
            return damage_amount

        # Nanocytes can not penetrate shields, but if there's no shield there, everything gets passed through... uh oh.
        if hit_event._type == DamageType.Nanocyte:
            if old_strength > 0:
                hit_event.notify_owner(f"Nanocytes splashed harmlessly against {self.container.name}'s shield.")
                return 0
            else:
                return hit_event.amount
        elif hit_event._type == DamageType.EMP:
            if old_strength >= damage_amount * 2:
                # All damage to shield
                damage_amount = damage_amount * 2
            else:
                # Add half of the shield strength to the damage to simulate
                # double damage to shields, but not anything else.
                damage_amount += old_strength // 2

        self.strengths[shield_quadrant] -= damage_amount
        if old_strength >= damage_amount:
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

    def post_round_reset(self):
        super().post_round_reset()
        for qdrt in ['N', 'E', 'S', 'W']:
            if self.strengths[qdrt] > self.max_strengths[qdrt]:
                self.add_internal_event(f"Shield {qdrt} boost dissipated: now at {self.strengths[qdrt]}.")
                self.strengths[qdrt] = self.max_strengths[qdrt]
