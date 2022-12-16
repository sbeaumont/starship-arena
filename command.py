import re
from collections import defaultdict
import logging
from enum import Enum
from typing import Protocol, runtime_checkable
from objectinspace import ObjectInSpace

logger = logging.getLogger(__name__)
COMMAND_PATTERN: str = r"^([A-Z|a-z]+)((\s*(-?[A-Z|a-z|0-9]+))*)$"

Cmd = Enum("Cmd", ['Turn', 'Accelerate', 'Fire', 'Replenish'])


@runtime_checkable
class Commandable(Protocol):
    commands: list

    def accelerate(self, delta_v: int):
        ...

    def turn(self, angle: int):
        ...

    def fire(self, weapon_name: str, target_or_direction) -> ObjectInSpace:
        ...

    def add_event(self, event: str):
        ...


class Command(object):
    def __init__(self, name: Cmd, original_text: str, **params):
        self.text = original_text
        self._name = name
        self._params = params

    @property
    def name(self) -> Cmd:
        return self._name

    @property
    def value(self):
        return self._params['value']

    @value.setter
    def value(self, value):
        self._params['value'] = value

    def param(self, name):
        return self._params[name]

    def __repr__(self):
        return f"Command(name='{self.name}', params='{self._params}')"

    def __str__(self):
        if len(self._params.keys()) == 1:
            return f"{self.name.name}({self.value})"
        else:
            param_str = ', '.join([f'{k}={v}' for k, v in self._params.items()])
            return f"{self.name.name}({param_str})"


class CommandSet(object):
    """The set of commands for one ship for one tick. Manipulates the ship in the correct order."""
    def __init__(self):
        self.acceleration: Command = None
        self.turning: Command = None
        self.weapons = dict()
        self.utilities = list()
        self.other = dict()

    def add(self, cmd: Command):
        match cmd.name:
            case Cmd.Accelerate:
                self._add_accelerate_command(cmd)
            case Cmd.Turn:
                self._add_turn_command(cmd)
            case Cmd.Fire:
                weapon_name = cmd.param('weapon_name')
                if weapon_name in self.weapons:
                    logger.warning(f"Can not add second fire command for same weapon {cmd}")
                else:
                    self.weapons[weapon_name] = cmd
            case Cmd.Replenish:
                self.other[Cmd.Replenish] = cmd

    def _add_turn_command(self, cmd: Command):
        """Ensure that multiple accelerate commands are added into a single command."""
        if self.turning:
            logger.warning(f"Double command for single tick: adding {str(self.turning)} to {str(cmd)}")
            self.turning.value += cmd.value
            self.turning.text = ' '.join((self.turning.text, cmd.text))
        else:
            self.turning = cmd

    def _add_accelerate_command(self, cmd: Command):
        """Ensure that multiple accelerate commands are added into a single command."""
        if self.acceleration:
            logger.warning(f"Double command for single tick: adding {str(self.acceleration)} to {str(cmd)}")
            self.acceleration.value += cmd.value
            self.acceleration.text = ' '.join((self.acceleration.text, cmd.text))
        else:
            self.acceleration = cmd

    def pre_move_commands(self, ship: Commandable):
        # First handle acceleration
        if self.acceleration:
            ship.add_event(f'Executing command "{self.acceleration.text}"')
            ship.accelerate(self.acceleration.value)
        # Then turning
        if self.turning:
            ship.add_event(f'Executing command "{self.turning.text}"')
            ship.turn(self.turning.value)

    def post_move_commands(self, ship: Commandable, objects_in_space: dict, new_objects: list, tick: int):
        # Then utilities
        # Finally, fire weapons
        for wpn_cmd in self.weapons.values():
            ship.add_event(f'Executing command "{wpn_cmd.text}"')
            ois = ship.fire(wpn_cmd.param('weapon_name'), wpn_cmd.param('at'))
            if ois:
                objects_in_space[ois.name] = ois
                new_objects.append(ois)
        if Cmd.Replenish in self.other:
            ship.add_event(f'Executing command "Replenish"')
            ship.replenish(objects_in_space)

    def __str__(self):
        util_str = ', '.join([str(cmd) for cmd in self.utilities])
        wpn_str = ', '.join([str(cmd) for cmd in self.weapons.values()])
        other_str = ', '.join([str(cmd) for cmd in self.other.values()])
        return f"Commands(A: {str(self.acceleration)} T: {str(self.turning)} U: {util_str} W: {wpn_str} O: {other_str})"


def read_command_file(command_file_name: str) -> dict:
    """Read a command file with the commands for a ship."""
    with open(command_file_name) as infile:
        logger.info(f"Reading {command_file_name}")
        lines = [line.strip().split(':') for line in infile.readlines() if not line.isspace()]

    commands = defaultdict(CommandSet)
    line_nr = 1
    for t, c in lines:
        tick = int(t.strip())
        cmds = re.finditer(COMMAND_PATTERN, c.strip())
        for cmd in cmds:
            cmd_text = cmd.group(0)
            name = cmd.group(1)
            params = cmd.group(2).split()
            match name:
                case 'H' | 'R':
                    # H<degrees> -> Turn right
                    commands[tick].add(Command(Cmd.Turn, cmd_text, value=int(params[0])))
                case 'L':
                    # L90 -> Turn left
                    commands[tick].add(Command(Cmd.Turn, cmd_text, value=-int(params[0])))
                case 'A':
                    # A30 -> Accelerate faster (+) or slow down/reverse (-)
                    commands[tick].add(Command(Cmd.Accelerate, cmd_text, value=int(params[0])))
                case 'F' | 'Fire':
                    # Fire <Weapon Name> <Direction or Target name>
                    commands[tick].add(Command(Cmd.Fire, cmd_text, weapon_name=params[0], at=params[1]))
                case 'Replenish':
                    # Replenish
                    commands[tick].add(Command(Cmd.Replenish, cmd_text))
                case _:
                    logger.warning(f"{command_file_name}: Unknown command {cmd} in line {line_nr}")
        line_nr += 1
    logger.info(f"Read command file {command_file_name}")
    return commands
