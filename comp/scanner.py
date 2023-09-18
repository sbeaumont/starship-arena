from comp.weapon import Weapon
from ois.event import ScanEvent
from cfg import max_scan
from comp.component import DirectionParameter, NumberInRangeParameter


class Gravscan(Weapon):
    """Active scanner that is 'fired' in a specific direction."""
    def __init__(self, name: str):
        super().__init__(name)
        self.strength = 100
        self.energy_per_pulse = 10
        self.default_scan_cone = 90
        self.max_scan_distance = max_scan(500)
        self.min_scan_distance = max_scan(50)
        self.active = False

    @property
    def expected_parameters(self):
        return [DirectionParameter('direction', self),
                NumberInRangeParameter('scan cone', self, (30, 360))]

    def fire(self, params: dict, objects_in_space: dict):
        direction = params['direction'].value
        scan_cone = params['scan cone'].value

        if self.container.battery >= self.energy_per_pulse:
            self.firing_arc = (direction - scan_cone // 2, direction + scan_cone // 2)
            coefficient = (self.max_scan_distance - self.min_scan_distance) / 330
            scan_distance = int(self.max_scan_distance - (coefficient * (scan_cone - 30)))
            self.container.battery -= self.energy_per_pulse
            self.add_internal_event(f"Gravscan {self.name} used {self.energy_per_pulse} energy.")
            self.add_internal_event(f"Gravscan {self.name} activated (width {scan_cone}, distance {scan_distance}).")
            pings = 0
            for ois in objects_in_space.values():
                if self.in_firing_arc(self.container.direction_to(ois.pos)):
                    if ois.modify_scan_range(self.container.distance_to(ois.pos)) <= scan_distance:
                        pings += 1
                        self.container.add_event(ScanEvent.create_scan(self.container, ois))
            self.add_internal_event(f"Gravscan got {pings} pings.")
        else:
            self.add_internal_event(f"Not enough energy to fire Gravscan.")
        self.firing_arc = None

    @property
    def description(self):
        return f"Gravscan ({self.strength})"


