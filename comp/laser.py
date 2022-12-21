from comp.weapon import Weapon
from ois.event import InternalEvent, HitEvent, DrawType


class Laser(Weapon):
    """A laser that directly fires at another named ship."""
    def __init__(self, name, firing_arc=None):
        super().__init__(name, firing_arc)
        self.max_temperature = 100
        self.energy_per_shot = 5
        self.damage_per_shot = 10
        self.heat_per_shot = 20

        self.temperature = 0

    @property
    def temperature_ok(self):
        return self.temperature <= self.max_temperature

    @property
    def energy_ok(self):
        return self.owner.battery >= self.energy_per_shot

    def can_fire_at(self, ois):
        return self.temperature_ok and self.energy_ok and self.owner.can_scan(ois)

    def tick(self, tick_nr):
        if self.temperature > 0:
            self.temperature -= 5
        if self.temperature < 0:
            self.temperature = 0

    def reset(self):
        self.temperature = 0

    def fire(self, target_name: str, objects_in_space=None):
        target_ship = objects_in_space.get(target_name, None)
        if not target_ship:
            self.owner.add_event(InternalEvent(f"Can't fire {self.name}. Unknown ship name: {target_name}"))
            return None

        firing_angle = self.owner.direction_to(target_ship.xy)
        if self.firing_arc and not self.in_firing_arc(firing_angle):
            self.owner.add_event(InternalEvent(f"{self.name} can not fire at angle {firing_angle}: {self.firing_arc}."))
            return None

        if target_ship and self.can_fire_at(target_ship):
            hit_event = HitEvent((self.owner.pos, target_ship.pos), 'Laser', self.owner, target_ship, self.damage_per_shot, DrawType.Line)
            target_ship.take_damage_from(hit_event)
            self.owner.add_event(hit_event)
        else:
            temp_status = 'Overheated' if not self.temperature_ok else ''
            battery_status = 'Low Battery' if not self.energy_ok else ''
            target_status = 'Target not visible' if not self.owner.can_scan(target_ship) else ''
            self.owner.add_event(InternalEvent(f"Ship {self.owner.name} failed to laser {target_name}: {' '.join([temp_status, battery_status, target_status])}"))
        self.temperature += self.heat_per_shot
        self.owner.battery -= self.energy_per_shot

    @property
    def status(self):
        return {
            'Temperature': f"{self.temperature}/{self.max_temperature}",
            'Firing Arc': self.firing_arc if self.firing_arc else '360'
        }
