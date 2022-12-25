from comp.weapon import Weapon
from ois import builder
from ois.event import InternalEvent


class MissileLauncher(Weapon):
    """Fires Rockets in a given direction. Best to point it away from your friends."""
    def __init__(self, name: str, payload_type, initial_load: int, firing_arc=None):
        super().__init__(name, firing_arc)
        self.missile_number = 0
        self.initial_load = initial_load
        self.ammo = initial_load
        self.payload_type = payload_type

    def _create_missile(self, name, heading):
        missile = builder.create(name, self.payload_type.__name__, self.owner.xy, self.current_tick, owner=self.owner, heading=heading)
        return missile

    def tick(self, tick_nr):
        self.current_tick = tick_nr

    def fire(self, direction: str, objects_in_space=None):
        firing_angle = int(direction)
        if self.ammo <= 0:
            self.add_internal_event(f"{self.name} could not fire: empty.")
            return None

        if self.firing_arc and not self.in_firing_arc(firing_angle):
            self.add_internal_event(f"{self.name} can not fire at angle {firing_angle}: {self.firing_arc}.")
            return None

        self.missile_number += 1
        self.ammo -= 1
        heading = (self.container.heading + int(direction)) % 360
        name = f'{self.container.name}-{self.payload_type.name}-{self.name}-{self.missile_number}'
        self.add_internal_event(f"Launcher {self.name} fired {name} in direction {int(direction)}")
        return self._create_missile(name, heading=heading)

    @property
    def status(self):
        return {
            'Ammo': f"{self.ammo} {self.payload_type.name}",
            'Firing Arc': self.firing_arc if self.firing_arc else '360'
        }

    @property
    def description(self):
        fa = self.firing_arc if self.firing_arc else "(360)"
        return f"Launcher ({self.initial_load} {self.payload_type.name} {fa})"

    def reset(self):
        self.ammo = self.initial_load
