from ois import builder
from ois.event import InternalEvent, HitEvent, DrawType


class Weapon(object):
    """An object that is attached to an owner (Ship) and can damage other objects in space."""
    def __init__(self, name: str, firing_arc: tuple=None):
        self.name = name
        self.owner = None
        if firing_arc:
            assert len(firing_arc) == 2
            assert 0 <= firing_arc[0] <= 360
            assert 0 <= firing_arc[1] <= 360
        self.firing_arc = firing_arc

    def attach(self, owner):
        self.owner = owner

    def fire(self, direction_or_target: str, objects_in_space=None):
        return None

    def tick(self, tick_nr):
        pass

    def reset(self):
        pass

    def in_firing_arc(self, angle):
        """Determine if an angle is in the firing arc of the weapon."""
        if not self.firing_arc:
            # If no arc is given, 360 degree arc is assumed.
            return True

        angle = angle % 360
        left, right = self.firing_arc
        if left > right:
            # Arc passes through 0, e.g. 270 -> 0 -> 90
            return (left <= angle) or (angle <= right)
        else:
            # Arc does not pass through 0, e.g. 90 -> 225
            return left <= angle <= right

    @property
    def status(self):
        raise NotImplementedError


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
            self.owner.add_event(InternalEvent(f"{self.name} could not fire: empty."))
            return None

        if self.firing_arc and not self.in_firing_arc(firing_angle):
            self.owner.add_event(InternalEvent(f"{self.name} can not fire at angle {firing_angle}: {self.firing_arc}."))
            return None

        self.missile_number += 1
        self.ammo -= 1
        heading = (self.owner.heading + int(direction)) % 360
        name = f'{self.owner.name}-{self.payload_type.name}-{self.name}-{self.missile_number}'
        self.owner.add_event(InternalEvent(f"Launcher {self.name} fired {name} in direction {int(direction)}"))
        return self._create_missile(name, heading=heading)

    @property
    def status(self):
        return {
            'Ammo': f"{self.ammo} {self.payload_type.name}",
            'Firing Arc': self.firing_arc if self.firing_arc else '360'
        }

    def reset(self):
        self.ammo = self.initial_load


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
            self.owner.add_event(hit_event)
            target_ship.take_damage_from(hit_event)
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
