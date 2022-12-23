from comp.weapon import Weapon
from ois.event import InternalEvent, HitEvent, DrawType


class Laser(Weapon):
    """A laser that directly fires at another named ship."""
    max_temperature = 100
    energy_per_shot = 5
    heat_per_shot = 20

    def __init__(self, name: str, strength: int, firing_arc=None):
        super().__init__(name, firing_arc)
        self.strength = strength
        self.temperature = 0

    # ---------------------------------------------------------------------- QUERIES

    @property
    def temperature_ok(self):
        return self.temperature <= self.max_temperature

    @property
    def energy_ok(self):
        return self.owner.battery >= self.energy_per_shot

    def can_fire_at(self, ois):
        return self.temperature_ok and self.energy_ok and self.owner.can_scan(ois) and self.damage_to(ois)

    def damage_to(self, target):
        """Damage reduces by 1 per distance."""
        damage = round(self.strength - self.owner.distance_to(target.pos))
        return damage if damage >= 0 else 0

    # ---------------------------------------------------------------------- COMMANDS

    def fire(self, target_name: str, objects_in_space=None):
        target_ship = objects_in_space.get(target_name, None)
        if not target_ship:
            self.owner.add_event(InternalEvent(f"Can't fire {self.name}. Unknown ship name: {target_name}"))
            return None

        firing_angle = self.owner.direction_to(target_ship.xy)
        if self.firing_arc and not self.in_firing_arc(firing_angle):
            self.owner.add_event(InternalEvent(f"{self.name} can not fire at angle {firing_angle}: {self.firing_arc}."))
            return None

        if self.owner.can_scan(target_ship) and not self.damage_to(target_ship):
            self.owner.add_event(InternalEvent(f"{self.name} strength too low: no damage at this distance."))
            return None

        if target_ship and self.can_fire_at(target_ship):
            hit_event = HitEvent((self.owner.pos, target_ship.pos), 'Laser', self.owner, target_ship, self.damage_to(target_ship), DrawType.Line)
            target_ship.take_damage_from(hit_event)
            self.owner.add_event(hit_event)
        else:
            temp_status = 'Overheated' if not self.temperature_ok else ''
            battery_status = 'Low Battery' if not self.energy_ok else ''
            target_status = 'Target not visible' if not self.owner.can_scan(target_ship) else ''
            self.owner.add_event(InternalEvent(f"Ship {self.owner.name} failed to laser {target_name}: {' '.join([temp_status, battery_status, target_status])}"))
        self.temperature += self.heat_per_shot
        self.owner.battery -= self.energy_per_shot

    # ---------------------------------------------------------------------- ENGINE INTERFACE

    def tick(self, tick_nr):
        if self.temperature > 0:
            self.temperature -= 5
        if self.temperature < 0:
            self.temperature = 0

    def reset(self):
        self.temperature = 0

    @property
    def status(self):
        return {
            'Temperature': f"{self.temperature}/{self.max_temperature}",
            'Strength': self.strength,
            'Firing Arc': self.firing_arc if self.firing_arc else '360'
        }
