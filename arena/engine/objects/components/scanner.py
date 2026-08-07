from math import sqrt

from arena.engine.history import Tick
from arena.engine.world import World
from arena.engine.objects.components.weapon import Weapon
from arena.engine.objects.event import ScanEvent
from arena.engine.objects.component import DirectionParameter, NumberInRangeParameter

from arena.cfg import max_scan


class Gravscan(Weapon):
    """Active scanner that is 'fired' in a specific direction.

    `strength` is a scan rating like a hull's, so it runs through `max_scan` the same way and the
    two can be read against each other. A pulse has that much reach at its narrowest and spreads
    the same energy thinner as the cone widens."""

    narrowest_cone = 30

    def __init__(self, name: str, strength: int = 200):
        super().__init__(name)
        self.strength = strength
        self.energy_per_pulse = 10
        self.default_firing_arc = self.firing_arc

    @property
    def max_scan_distance(self) -> int:
        """How far the narrowest pulse this can make reaches."""
        return max_scan(self.strength)

    @property
    def expected_parameters(self):
        return [DirectionParameter('direction', self),
                NumberInRangeParameter('scan cone', self, (self.narrowest_cone, 360))]

    def reach_of(self, scan_cone: int) -> int:
        """How far a pulse that wide gets: see docs/ship-balance.md on pointing it."""
        return int(self.max_scan_distance * sqrt(self.narrowest_cone / scan_cone))

    def fire(self, params: dict, world: World, tick: Tick):
        direction = params['direction'].value
        scan_cone = params['scan cone'].value

        if self.container.battery >= self.energy_per_pulse:
            # Both ends folded into the circle, or an arc straddling the bow sweeps only its
            # starboard half.
            self.firing_arc = ((direction - scan_cone // 2) % 360,
                               (direction + scan_cone // 2) % 360)
            scan_distance = self.reach_of(scan_cone)
            self.container.battery -= self.energy_per_pulse
            self.add_internal_event(f"Gravscan {self.name} used {self.energy_per_pulse} energy.")
            self.add_internal_event(f"Gravscan {self.name} activated (width {scan_cone}, distance {scan_distance}).")
            pings = 0
            for ois in world.objects.values():
                if self.in_firing_arc(self.container.direction_to(ois.pos)):
                    if self.container.distance_to(ois.pos) <= ois.modify_scan_range(scan_distance):
                        pings += 1
                        self.container.add_event(ScanEvent.create_scan(self.container, ois))
            self.add_internal_event(f"Gravscan got {pings} pings.")
        else:
            self.add_internal_event(f"Not enough energy to fire Gravscan.")
        self.firing_arc = self.default_firing_arc

    @property
    def description(self):
        return f"Gravscan ({self.strength})"


