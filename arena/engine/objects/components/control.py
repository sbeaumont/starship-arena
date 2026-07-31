from abc import ABC, abstractmethod
from enum import Enum

from arena.engine.history import Tick
from arena.engine.world import World
from arena.engine.objects.component import Component
from arena.engine.objects.components.laser import Laser
from arena.engine.objects.missile import Missile
from arena.engine.objects.mine import Mine
from arena.engine.objects.ship import Ship
from arena.engine.command import CommandLine, Command


class Controller(Component, ABC):
    """Component that acts as an NPC "crewmember"."""
    @property
    @abstractmethod
    def status(self) -> dict:
        return dict()

    @abstractmethod
    def decide(self, world: World, tick: Tick):
        pass

    def add_command(self, tick_nr: int, command: str, world):
        cmd = Command.for_command_line(CommandLine(f"{tick_nr}: {command}"), self.container, world)
        self.add_internal_event(f"{self.name}: adding command '{cmd.command_line.text}'")
        self.container.commands[cmd.tick].add(cmd)


class Pilot(Controller):
    def __init__(self):
        super().__init__('Pilot')
        self.target_name = ''

    @property
    def status(self) -> dict:
        return {'Target': self.target_name}

    def set_current_target(self, target_name: str):
        if not self.target_name or self.target_name != target_name:
            self.target_name = target_name
            self.add_internal_event(f"{self.name}: setting target to {self.target_name}")

    def decide(self, world: World, tick: Tick):
        if self.target_name:
            target_scan = [s for s in self.container.scans if s.source.name == self.target_name]
            if target_scan:
                source = target_scan[0]
                direction_to_target = round(self.container.direction_to(source.pos))
                turn_command = f"R{direction_to_target}" if direction_to_target >= 0 else f"L{abs(direction_to_target)}"
                self.add_command(tick.tick + 1, turn_command, world)


class TargetingMode(str, Enum):
    """The 3.10-compatible spelling of a StrEnum: members are strings, and printing one gives
    its value rather than 'TargetingMode.Defensive'. Same shape as DamageType."""
    Defensive = 'Defensive'
    Offensive = 'Offensive'

    def __str__(self):
        return self.value

class Gunner(Controller):
    def __init__(self):
        super().__init__('Gunner')
        self.target_mode = TargetingMode.Defensive

    def set_targeting_mode(self, mode: TargetingMode):
        if mode != self.target_mode:
            self.add_internal_event(f"{self.name}: setting targeting mode to {mode}")
            self.target_mode = mode

    @property
    def status(self) -> dict:
        return {'Target Mode': self.target_mode}

    def decide(self, world: World, tick: Tick):
        enemies = [s.source for s in self.container.scans_sorted_by('distance') if s.source.faction != self.container.faction]
        for name, laser in self.lasers.items():
            took_a_shot = False
            for enemy in enemies:
                if (self.target_mode == TargetingMode.Defensive and isinstance(enemy, (Missile, Mine))) or \
                    (self.target_mode == TargetingMode.Offensive and isinstance(enemy, Ship)):
                    took_a_shot = self.fire_laser(laser, enemy, tick, world)
                    if took_a_shot:
                        break
            if not took_a_shot and enemies:
                self.add_internal_event(f"{self.name}: Firing at closest enemy.")
                self.fire_laser(laser, enemies[0], tick, world)

    def fire_laser(self, laser, enemy, tick, ois):
        if not enemy.is_destroyed and laser.can_fire_at(enemy):
            self.add_command(tick.tick + 1, f"Fire {laser.name} {enemy.name}", ois)
            return True
        return False

    @property
    def lasers(self) -> dict:
        return {name: weapon for name, weapon in self.container.weapons.items() if isinstance(weapon, Laser)}