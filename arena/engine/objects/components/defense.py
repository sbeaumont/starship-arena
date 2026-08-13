from arena.engine.objects.component import Component, ComponentParameter, NumberInRangeParameter
from arena.engine.objects.geometry import Point
from arena.engine.objects.machineinspace import MachineInSpace
from arena.engine.objects.event import DamageType, Effect, Outcome


class QuadrantParameter(ComponentParameter):
    """Which face of the shield an order is about."""

    @property
    def kind(self) -> str:
        return 'quadrant'

    @property
    def choices(self) -> list:
        return list(self.component.max_strengths)

    @property
    def is_valid(self):
        assert self._input is not None
        self.feedback.clear()
        if self._input not in self.choices:
            self.feedback.append(f"{self._input} is not one of ({', '.join(self.choices)}).")
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
        """Which shield quadrant an attack lands on.

        Quadrants are relative to the ship: N is the front 90 degrees (+/-45), so the
        absolute bearing of the attack has to be turned into a bearing relative to where
        the ship is pointing. Turning to present a stronger shield therefore works."""
        heading = (self.container.heading_to(source_location) - self.container.heading) % 360
        for angles, name in self.quadrants.items():
            if (angles[0] > angles[1]) and (heading >= angles[0]) or (heading <= angles[1]):
                # North
                return name
            elif angles[0] <= heading <= angles[1]:
                return name
        assert False, f"No quadrant found {source_location.as_tuple}, {heading}"

    @property
    def expected_parameters(self):
        return [QuadrantParameter('quadrant', self),
                NumberInRangeParameter('amount', self, (0, 2 * max(self.max_strengths.values())))]

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

    def take_damage_from(self, damage_type: DamageType, damage: int, struck_from: Point) -> Effect:
        """Take what reached this shield, and answer with what became of it.

        Handed the kind of harm, how much of it arrived and where from, which is everything a
        shield needs. It never sees the blow itself, so it cannot know whose it was, whether it
        scores, or what to call whoever fired: those are not a shield's business."""
        quadrant = self.quadrant_of(struck_from)
        strength = self.strengths[quadrant]

        if strength == 0:
            return Effect(self.name, Outcome.Unaffected, 0, 0, damage)

        if damage_type == DamageType.Nanocyte:
            # Nanocytes cannot get through a shield at all, and blunt themselves trying.
            return Effect(self.name, Outcome.Unaffected, 0, 0, 0)
        if damage_type == DamageType.EMP:
            # Twice the bite against a shield, and no more than the shield can take.
            damage = damage * 2 if strength >= damage * 2 else damage + strength // 2

        taken = min(strength, damage)
        self.strengths[quadrant] = strength - taken
        if damage <= strength:
            self.add_internal_event(f"Shield {quadrant} hit for {damage}. "
                                    f"Remaining strength: {self.strengths[quadrant]}")
            return Effect(self.name, Outcome.Damaged, taken, taken // 2, 0)

        through = damage - taken
        self.add_internal_event(f"Hit on shield {quadrant} broke the shield: {through} passed through.")
        return Effect(self.name, Outcome.Breached, taken,
                      taken // 2 + self.shield_break_score, through)

    # ---------------------------------------------------------------------- ENGINE HANDLERS

    def reset(self):
        self.strengths = {q: max(s, self.max_strengths[q]) for q, s in self.strengths.items()}

    def post_round_reset(self):
        super().post_round_reset()
        for qdrt in ['N', 'E', 'S', 'W']:
            if self.strengths[qdrt] > self.max_strengths[qdrt]:
                self.add_internal_event(f"Shield {qdrt} boost dissipated: now at {self.strengths[qdrt]}.")
                self.strengths[qdrt] = self.max_strengths[qdrt]
