from comp.weapon import Weapon
from ois.event import HitEvent, DrawType
from comp.component import ObjectByNameParameter


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
        return self.container.battery >= self.energy_per_shot

    def can_fire_at(self, ois):
        return self.temperature_ok and self.energy_ok and self.container.can_scan(ois) and self.damage_to(ois)

    def damage_to(self, target):
        """Damage reduces by 1 per distance."""
        damage = round(self.strength - self.container.distance_to(target.pos))
        return damage if damage >= 0 else 0

    @property
    def expected_parameters(self):
        return [ObjectByNameParameter('target', self)]

    # ---------------------------------------------------------------------- COMMANDS

    def fire(self, params: dict, objects_in_space: dict):
        target_ship = params['target'].value
        if not target_ship:
            self.add_internal_event(f"Can't fire {self.name}. Unknown ship name: {target_name}")
            return None

        firing_angle = self.owner.direction_to(target_ship.xy)
        if self.firing_arc and not self.in_firing_arc(firing_angle):
            self.add_internal_event(f"{self.name} can not fire at angle {round(firing_angle, 1)}: {self.firing_arc}.")
            return None

        if self.container.can_scan(target_ship) and not self.damage_to(target_ship):
            self.add_internal_event(f"{self.name} strength too low: no damage at this distance.")
            return None

        if target_ship and self.can_fire_at(target_ship):
            hit_event = HitEvent((self.container.pos, target_ship.pos), 'Laser', self.owner, target_ship, self.damage_to(target_ship), DrawType.Line)
            target_ship.take_damage_from(hit_event)
            self.owner.add_event(hit_event)
        else:
            temp_status = 'Overheated' if not self.temperature_ok else ''
            battery_status = 'Low Battery' if not self.energy_ok else ''
            target_status = 'Target not visible' if not self.owner.can_scan(target_ship) else ''
            self.add_internal_event(f"Ship {self.owner.name} failed to laser {target_ship.name}: {' '.join([temp_status, battery_status, target_status])}")
        self.temperature += self.heat_per_shot
        self.container.battery -= self.energy_per_shot

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
        st = super().status
        st['Temperature'] = f"{self.temperature}/{self.max_temperature}"
        st['Strength'] = self.strength
        return st

    @property
    def description(self):
        fa = self.firing_arc if self.firing_arc else "(360)"
        return f"{self.__class__.__name__} ({self.strength} {fa})"
