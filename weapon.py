from history import DrawableEvent, History, RocketSnapshot
from objectinspace import Rocket


class Weapon(object):
    """An object that is attached to an owner (Ship) and can damage other objects in space."""
    def __init__(self, name: str):
        self.name = name
        self.owner = None

    def attach(self, owner):
        self.owner = owner

    def fire(self, direction_or_target: str):
        return None

    def tick(self, tick_nr):
        pass

    def reset(self):
        pass

    @property
    def status(self):
        raise NotImplementedError


class RocketLauncher(Weapon):
    """Fires Rockets in a given direction. Best to point it away from your friends."""
    def __init__(self, name: str, rocket_type, initial_load: int = 5):
        super().__init__(name)
        self.rocket_number = 1
        self.initial_load = initial_load
        self.ammo = initial_load
        self.rocket_type = rocket_type

    def create_rocket(self, name, heading):
        rocket = Rocket(name, self.owner.xy, self.rocket_type, self.owner, heading)
        rocket.history = History(rocket, RocketSnapshot, self.current_tick)
        return rocket

    def tick(self, tick_nr):
        self.current_tick = tick_nr

    def fire(self, direction: str):
        if self.ammo > 0:
            rocket_heading = (self.owner.heading + int(direction)) % 360
            rocket_name = f'{self.owner.name}-Rocket-{self.name}-{self.rocket_number}'
            self.rocket_number += 1
            self.owner.add_event(f"{self.name} fired rocket {rocket_name} in direction {int(direction)}")
            rocket = self.create_rocket(rocket_name, heading=rocket_heading)
            self.ammo -= 1
            return rocket
        else:
            self.owner.add_event(f"{self.name} could not fire: empty.")
            return None

    @property
    def status(self):
        return {'Ammo': self.ammo}

    def reset(self):
        self.ammo = self.initial_load


class Laser(Weapon):
    """A laser that directly fires at another named ship."""
    def __init__(self, name):
        super().__init__(name)
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

    def target_visible(self, target_name: str):
        return target_name in self.owner.scans

    def can_fire_at(self, target_name: str):
        return self.temperature_ok and self.energy_ok and self.target_visible(target_name)

    def tick(self, tick_nr):
        if self.temperature > 0:
            self.temperature -= 5
        if self.temperature < 0:
            self.temperature = 0

    def reset(self):
        self.temperature = 0

    def fire(self, target_name: str):
        if self.can_fire_at(target_name):
            target_ship = self.owner.scans[target_name].ois
            self.owner.add_event(
                DrawableEvent('Laser', (self.owner.pos, target_ship.pos), f"{self.name} lasered {target_name} for {self.damage_per_shot} damage"))
            target_ship.take_damage_from(
                DrawableEvent('Laser', (self.owner.pos, target_ship.pos), f"Hit by {self.owner.name}'s laser for {self.damage_per_shot} damage"), self.owner.pos, self.damage_per_shot)
        else:
            temp_status = 'Overheated' if not self.temperature_ok else ''
            battery_status = 'Low Battery' if not self.energy_ok else ''
            target_status = 'Target not visible' if not self.target_visible(target_name) else ''
            self.owner.add_event(f"Ship {self.owner.name} failed to laser {target_name}: {' '.join([temp_status, battery_status, target_status])}")
        self.temperature += self.heat_per_shot
        self.owner.battery -= self.energy_per_shot

    @property
    def status(self):
        return {'Temperature': f"{self.temperature}/{self.max_temperature}"}