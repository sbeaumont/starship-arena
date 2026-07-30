from typing import Protocol, runtime_checkable

from arena.engine.history import Tick, TICK_ZERO
from arena.engine.objects.components.weapon import Weapon
from arena.engine.objects.objectinspace import Vector
from arena.engine.objects.component import DirectionParameter


@runtime_checkable
class PayloadType(Protocol):
    @property
    def name(self):
        ...

    def create(self, name: str, vector: Vector, owner=None, tick: Tick = TICK_ZERO):
        ...


class Launcher(Weapon):
    """Fires Rockets in a given direction. Best to point it away from your friends."""
    def __init__(self, name: str, payload_type: PayloadType, initial_load: int, firing_arc=None):
        super().__init__(name, firing_arc)
        self.missile_number = 0
        self.initial_load = initial_load
        self.ammo = initial_load
        self.payload_type = payload_type

    def _create_missile(self, name, heading, tick: Tick):
        vector = Vector(pos=self.container.vector.pos, heading=heading, speed=self.container.speed)
        payload = self.payload_type.create(name, vector, owner=self.owner, tick=tick)
        # Born inside its own reach, a payload acts on the ship that just fired it: a Rocket
        # triggering on its launch tick takes 50 hull off its own launcher.
        payload.place_at(payload.xy.translate(heading, payload.range + 1))
        return payload

    @property
    def expected_parameters(self):
        return [DirectionParameter('direction', self)]

    def fire(self, params: dict, objects_in_space: dict, tick: Tick):
        firing_angle = params['direction'].value

        if self.ammo <= 0:
            self.add_internal_event(f"{self.name} could not fire: ammo empty.")
            return None

        if self.firing_arc and not self.in_firing_arc(firing_angle):
            self.add_internal_event(f"{self.name} can not fire at angle {firing_angle}: {self.firing_arc}.")
            return None

        self.missile_number += 1
        self.ammo -= 1
        heading = (self.container.heading + firing_angle) % 360
        name = f'{self.container.name}-{self.payload_type.name}-{self.name}-{self.missile_number}'
        self.add_internal_event(f"Launcher {self.name} fired {name} in direction {firing_angle}")
        return self._create_missile(name, heading=heading, tick=tick)

    @property
    def status(self):
        return {
            self.payload_type.name: self.ammo
        }

    @property
    def description(self):
        fa = self.firing_arc if self.firing_arc else "(360)"
        return f"Launcher ({self.initial_load} {self.payload_type.name} {fa})"

    def reset(self):
        self.ammo = self.initial_load
