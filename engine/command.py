import re
import logging
from collections import defaultdict
from enum import Enum, auto
from typing import Protocol, runtime_checkable

from ois.objectinspace import ObjectInSpace
from comp.defense import Shields
from ois.event import InternalEvent

logger = logging.getLogger(__name__)

COMMAND_PATTERN: str = r"^([A-Z|a-z]+)((\s*(-?[A-Z|a-z|0-9]+))*)$"


class Cmd(Enum):
    Turn = auto()
    Accelerate = auto()
    Fire = auto()
    Replenish = auto()
    Boost = auto()
    Activation = auto()


@runtime_checkable
class Commandable(Protocol):
    commands: list
    defense: list

    def accelerate(self, delta_v: int):
        ...

    def turn(self, angle: int):
        ...

    def fire(self, weapon_name: str, target_or_direction, objects_in_space: dict) -> ObjectInSpace:
        ...

    def try_replenish(self, objects_in_space: dict):
        ...

    def scan(self, objects_in_space: dict):
        ...

    def activation(self, name: str, on_off: bool):
        ...

    def add_event(self, event):
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

    def execute(self, commandable: Commandable, objects_in_space: dict, tick: int):
        pass

    def __repr__(self):
        return f"Command(name='{self.name}', params='{self._params}')"

    def __str__(self):
        if len(self._params.keys()) == 1:
            return f"{self.name.name}({self.value})"
        else:
            param_str = ', '.join([f'{k}={v}' for k, v in self._params.items()])
            return f"{self.name.name}({param_str})"


class AccelerateCommand(Command):
    def __init__(self, original_text: str, amount):
        super().__init__(Cmd.Accelerate, original_text)
        self.amount = int(amount)

    def merge(self, cmd_text, amount):
        self.amount += int(amount)
        self.text = ' '.join((self.text, cmd_text))

    def execute(self, target: Commandable, objects_in_space: dict, tick: int):
        target.add_event(InternalEvent(f'Executing command "{self.text}"'))
        target.accelerate(self.amount)


class ActivationCommand(Command):
    def __init__(self, original_text: str, comp_name: str, on_off: str):
        super().__init__(Cmd.Activation, original_text)
        assert on_off.lower() in ['yes', 'no', 'true', 'false', 'on', 'off']
        self.active = on_off.lower() in ['yes', 'true', 'on']
        self.comp_name = comp_name

    def execute(self, target: Commandable, objects_in_space: dict, tick: int):
        target.add_event(InternalEvent(f'Executing command "{self.text}"'))
        target.activation(self.comp_name, self.active)


class BoostCommand(Command):
    def __init__(self, original_text: str, quadrant, amount):
        super().__init__(Cmd.Boost, original_text)
        assert quadrant in ('N', 'E', 'S', 'W')
        self.quadrant = quadrant
        self.amount = int(amount)

    def execute(self, target: Commandable, objects_in_space: dict, tick: int):
        for d in target.defense:
            if isinstance(d, Shields):
                d.boost(self.quadrant, self.amount)
                break


class FireCommand(Command):
    def __init__(self, original_text: str, weapon_name, target_or_direction):
        super().__init__(Cmd.Fire, original_text)
        self.weapon_name = weapon_name
        self.target_or_direction = target_or_direction

    def execute(self, target: Commandable, objects_in_space: dict, tick: int):
        target.add_event(InternalEvent(f'Executing command "{self.text}"'))
        ois = target.fire(self.weapon_name, self.target_or_direction, objects_in_space)
        if ois:
            objects_in_space[ois.name] = ois


class ReplenishCommand(Command):
    def __init__(self, original_text: str):
        super().__init__(Cmd.Replenish, original_text)

    def execute(self, target: Commandable, objects_in_space: dict, tick: int):
        target.add_event(InternalEvent(f'Executing command "Replenish"'))
        target.try_replenish(objects_in_space)


class TurnCommand(Command):
    def __init__(self, original_text: str, direction, amount):
        super().__init__(Cmd.Turn, original_text)
        self.amount = int(amount) if direction in ('R', 'H') else -int(amount)

    def merge(self, cmd_text, direction, amount):
        assert direction in ('R', 'H', 'L')
        self.amount += int(amount) if direction in ('R', 'H') else -int(amount)
        self.text = ' '.join((self.text, cmd_text))

    def execute(self, target: Commandable, objects_in_space: dict, tick: int):
        target.add_event(InternalEvent(f'Executing command "{self.text}"'))
        target.turn(self.amount)


class CommandSet(object):
    """The set of commands for one ship for one tick. Manipulates the ship in the correct order."""
    def __init__(self):
        self.acceleration: Command = None
        self.turning: Command = None
        self.weapons: dict = dict()
        self.pre_move: list = list()
        self.post_move: list = list()

    def add(self, cmd: Command):
        match cmd.name:
            case Cmd.Accelerate:
                if self.acceleration:
                    self.acceleration.merge(cmd)
                else:
                    self.acceleration = cmd
            case Cmd.Turn:
                if self.turning:
                    self.turning.merge(cmd)
                else:
                    self.turning = cmd
            case Cmd.Fire:
                self.weapons[cmd.weapon_name] = cmd
            case Cmd.Activation:
                self.pre_move.append(cmd)
            case Cmd.Replenish | Cmd.Boost:
                self.post_move.append(cmd)
            case _:
                assert False, f"Unknown command: {cmd}"


def read_command_file(command_file_name: str) -> dict:
    """Read a command file with the commands for a ship."""
    with open(command_file_name) as infile:
        logger.info(f"Reading {command_file_name}")
        lines = [line.strip() for line in infile.readlines() if not line.isspace()]

    commands = defaultdict(CommandSet)
    line_nr = 1
    for line in lines:
        if line.startswith('#'):
            continue

        t, c = line.split(':')
        tick = int(t.strip())
        cmd = re.match(COMMAND_PATTERN, c.strip())
        cmd_text = cmd.group(0)
        name = cmd.group(1)
        params = cmd.group(2).split()
        match name:
            case 'L' | 'R':
                # L90 -> Turn left
                commands[tick].add(TurnCommand(cmd_text, name, int(params[0])))
            case 'A':
                # A30 -> Accelerate faster (+) or slow down/reverse (-)
                commands[tick].add(AccelerateCommand(cmd_text, int(params[0])))
            case 'F' | 'Fire':
                # Fire <Weapon Name> <Direction or Target name>
                commands[tick].add(FireCommand(cmd_text, weapon_name=params[0], target_or_direction=params[1]))
            case 'Replenish':
                # Replenish
                commands[tick].add(ReplenishCommand(cmd_text))
            case 'Boost':
                # Boost shield quadrant
                commands[tick].add(BoostCommand(cmd_text, quadrant=params[0], amount=int(params[1])))
            case 'Activation':
                # Turn components on or off
                commands[tick].add(ActivationCommand(cmd_text, comp_name=params[0], on_off=params[1]))
            case _:
                logger.warning(f"{command_file_name}: Unknown command {cmd} in line {line_nr}")
        line_nr += 1
    logger.info(f"Read command file {command_file_name}")
    return commands
