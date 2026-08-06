from arena.engine.objects.component import Component, NumberInRangeParameter


class Cloak(Component):
    """Bends scans around the ship, as hard as the energy put into it.

    `half_power` is the draw that halves an enemy's scan range; twice that quarters it. See
    docs/ship-balance.md for what the curve buys and what it costs."""

    # A cloak takes at most twice what the ship generates. Past that the curve has flattened
    # and no battery pays for it long enough to matter.
    max_draw_multiple = 2

    def __init__(self, name: str, half_power: float):
        super().__init__(name)
        self.half_power = half_power
        self.power = 0

    @property
    def expected_parameters(self):
        ceiling = self.max_draw_multiple * self.container.generators
        return [NumberInRangeParameter('power', self, (0, ceiling))]

    def power_up(self, amount: int):
        # Energy was drawn before this order ran, and scans are read after the move, so the
        # increase hides the ship this tick and has to be paid for in it.
        spent = min(amount - self.power, self.container.battery) if amount > self.power else 0
        self.container.battery -= spent
        self.power = amount
        self.add_internal_event(f"Cloak {self.name} drawing {self.power} energy a tick.")

    def use_energy(self):
        if self.power > self.container.battery:
            self.add_internal_event(f"Not enough energy for cloak {self.name}: shutting down.")
            self.power = 0
        else:
            self.container.battery -= self.power

    def modify_scan_range(self, scan_range: float) -> float:
        return round(scan_range * 0.5 ** (self.power / self.half_power), 1)

    @property
    def status(self) -> dict:
        return {
            'Power': self.power
        }

    @property
    def description(self):
        return f"Cloak (halves at {self.half_power})"