from arena.engine import Component, OnOffParameter


class Cloak(Component):
    energy_per_tick = 10

    def __init__(self, name, strength: float):
        super().__init__(name)
        self.active = False
        self.strength = strength

    @property
    def expected_parameters(self):
        return [OnOffParameter('on/off', self)]

    def activation(self, yes_no: bool):
        was_active = self.active
        self.active = yes_no
        self.add_internal_event(f"Cloak {self.name} {'activated' if self.active else 'deactivated'}.")
        if not was_active and self.active:
            self.use_energy()

    def use_energy(self):
        if self.active:
            if self.container.battery < self.energy_per_tick:
                self.active = False
                self.add_internal_event(f"Not enough energy for Cloak {self.name}: shutting down.")
            else:
                self.container.battery -= self.energy_per_tick
                self.add_internal_event(f"Cloak {self.name} used {self.energy_per_tick} energy.")

    def modify_scan_range(self, scan_range: float) -> float:
        if self.active:
            return round(scan_range * (1 - self.strength), 1)
        else:
            return scan_range

    @property
    def status(self) -> dict:
        return {
            'Active': 'Yes' if self.active else 'No'
        }

    @property
    def description(self):
        return f"Cloak ({self.strength})"


