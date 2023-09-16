import re
import logging
from collections import defaultdict
from enum import Enum, auto
from typing import Protocol, runtime_checkable

from ois.objectinspace import ObjectInSpace
from comp.defense import Shields
from ois.event import InternalEvent

logger = logging.getLogger('starship-arena.command')


def is_valid_number(value: str):
    return re.match(r"^-?\d+$", value) is not None


class ParsingError(Exception):
    pass


class Cmd(Enum):
    Turn = auto()
    Accelerate = auto()
    Fire = auto()
    Replenish = auto()
    Boost = auto()
    Activation = auto()
    Unknown = auto()


class CommandLine(object):
    COMMAND_PATTERN = r"^(\d+):\s*([A-Za-z]+)((\s*-?\w+)*)$"
    TICK_NAME_PARAMS = r"^(\d+):\s*([A-Za-z]+)(.*)$"

    def __init__(self, text: str):
        self.errors = list()
        self.text = text
        if self.is_valid:
            match = re.match(CommandLine.TICK_NAME_PARAMS, self.text)
            self.tick = int(match.group(1))
            self.name = match.group(2)
            self.params = match.group(3).split()
        else:
            self.tick = self.name = self.params = None
            self.errors.append("Missing basic '<tick number>:<command><parameter> <parameter>' structure")

    @property
    def is_valid(self) -> bool:
        return re.match(CommandLine.COMMAND_PATTERN, self.text) is not None

    def __repr__(self):
        if self.is_valid:
            return f"CommandLine({self.tick}, {self.name}, {self.params})"
        else:
            return f"CommandLine({self.text})"


@runtime_checkable
class Commandable(Protocol):
    commands: list
    defense: list

    def accelerate(self, delta_v: int):
        ...

    def turn(self, angle: int):
        ...

    def fire(self, weapon_name: str, target_or_direction, objects_in_space: dict, extra_params: list) -> ObjectInSpace:
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
    @classmethod
    def for_command_line(cls, command_line: CommandLine):
        match command_line.name.upper():
            case 'L' | 'R':
                # L90 -> Turn left
                return TurnCommand(command_line)
            case 'A':
                # A30 -> Accelerate faster (+) or slow down/reverse (-)
                return AccelerateCommand(command_line)
            case 'F' | 'FIRE' | 'SCAN':
                # Fire <Weapon Name> <Direction or Target name>
                return FireCommand(command_line)
            case 'REPLENISH':
                # Replenish
                return ReplenishCommand(command_line)
            case 'BOOST':
                # Boost shield quadrant
                return BoostCommand(command_line)
            case 'ACTIVATION' | 'ACTIVATE':
                # Turn components on or off
                return ActivationCommand(command_line)
            case _:
                logger.warning(f"Unknown command {command_line}")
                return UnknownCommand(command_line)

    def __init__(self, command_line: CommandLine):
        self.command_line = command_line
        self.param = dict()
        if self._check_params(self.command_line.params):
            self._fill_params(self.command_line.params)

    def _check_name(self) -> bool:
        ...

    def _check_params(self, params: list) -> bool:
        ...

    def _fill_params(self, params: list):
        ...

    def _get_type_name(self) -> Cmd:
        ...

    @property
    def is_valid(self) -> bool:
        return self.command_line.is_valid and self._check_params(self.command_line.params)

    @property
    def tick(self) -> int:
        return self.command_line.tick

    @property
    def name(self) -> Cmd:
        return self._get_type_name()

    @property
    def text(self) -> str:
        return self.command_line.text

    @property
    def value(self):
        return self.param.get('value')

    @value.setter
    def value(self, value):
        self.param['value'] = value

    @property
    def selector(self):
        return self.param.get('selector')

    @selector.setter
    def selector(self, value):
        self.param['selector'] = value

    def execute(self, commandable: Commandable, objects_in_space: dict, tick: int):
        commandable.add_event(InternalEvent(f'Executing command "{self.command_line.text}"'))

    def __repr__(self):
        return f"Command({self._get_type_name()}, {self.command_line})"


class AccelerateCommand(Command):
    def _check_params(self, params: list) -> bool:
        return len(params) == 1 and is_valid_number(params[0])

    def _fill_params(self, params: list):
        self.value = int(params[0])

    def _get_type_name(self) -> Cmd:
        return Cmd.Accelerate

    def merge(self, cmd):
        if not isinstance(cmd, AccelerateCommand):
            raise ValueError(f"Can not merge AccelerateCommand and {cmd.__class__}")
        self.value += int(cmd.value)

    def execute(self, target: Commandable, objects_in_space: dict, tick: int):
        super().execute(target, objects_in_space, tick)
        target.accelerate(self.value)


class ActivationCommand(Command):
    def _check_params(self, params: list) -> bool:
        if len(params) < 2:
            return False
        if params[1].lower() not in ['yes', 'no', 'true', 'false', 'on', 'off']:
            return False
        return params[0].isalnum()

    def _fill_params(self, params: list):
        self.selector = params[0]
        self.value = params[1].lower() in ['yes', 'true', 'on']
        if len(params) > 2:
            self.param['extra_params'] = params[2:]

    def _get_type_name(self) -> Cmd:
        return Cmd.Activation

    def execute(self, target: Commandable, objects_in_space: dict, tick: int):
        super().execute(target, objects_in_space, tick)
        target.activation(self.selector, self.value)


class BoostCommand(Command):
    def _check_params(self, params: list) -> bool:
        if len(params) != 2:
            return False
        if params[0].upper() not in ('N', 'E', 'S', 'W'):
            return False
        return is_valid_number(params[1])

    def _fill_params(self, params: list):
        self.selector = params[0]
        self.amount = int(params[1])

    def _get_type_name(self) -> Cmd:
        return Cmd.Boost

    def execute(self, target: Commandable, objects_in_space: dict, tick: int):
        super().execute(target, objects_in_space, tick)
        for d in target.defense:
            if isinstance(d, Shields):
                d.boost(self.selector, self.amount)
                break


class FireCommand(Command):
    def _check_params(self, params: list) -> bool:
        if len(params) < 2:
            return False
        if not params[0].isalnum():
            return False
        return params[1].isalnum() or is_valid_number(params[1])

    def _fill_params(self, params: list):
        self.selector = params[0]
        self.value = int(params[1]) if is_valid_number(params[1]) else params[1]
        if len(params) > 2:
            self.param['extra_params'] = params[2:]

    def _get_type_name(self) -> Cmd:
        return Cmd.Fire

    def execute(self, target: Commandable, objects_in_space: dict, tick: int):
        super().execute(target, objects_in_space, tick)
        fired_object = target.fire(self.selector, self.value, objects_in_space, self.param.get('extra_params', None))
        if fired_object:
            objects_in_space[fired_object.name] = fired_object


class ReplenishCommand(Command):
    def _check_params(self, params: list) -> bool:
        return len(params) == 0

    def _fill_params(self, params: list):
        pass

    def _get_type_name(self) -> Cmd:
        return Cmd.Replenish

    def execute(self, target: Commandable, objects_in_space: dict, tick: int):
        super().execute(target, objects_in_space, tick)
        target.try_replenish(objects_in_space)


class TurnCommand(Command):
    def _check_params(self, params: list) -> bool:
        if len(params) != 1:
            return False
        return is_valid_number(params[0])

    def _fill_params(self, params: list):
        self.value = int(params[0]) if self.command_line.name in ('R', 'H') else -int(params[0])

    def _get_type_name(self) -> Cmd:
        return Cmd.Turn

    def merge(self, cmd):
        self.value += cmd.value

    def execute(self, target: Commandable, objects_in_space: dict, tick: int):
        super().execute(target, objects_in_space, tick)
        target.turn(self.value)


class UnknownCommand(Command):
    def _check_params(self, params: list) -> bool:
        return False

    def _fill_params(self, params: list):
        pass

    def _get_type_name(self) -> Cmd:
        return Cmd.Unknown

    @property
    def is_valid(self) -> bool:
        # This command is never valid.
        return False

    def execute(self, target: Commandable, objects_in_space: dict, tick: int):
        target.add_event(f"Can't execute unknown command {self.command_line.text}")


class CommandSet(object):
    """The set of commands for one ship for one tick. Manipulates the ship in the correct order."""
    def __init__(self):
        self.acceleration: AccelerateCommand | None = None
        self.turning: TurnCommand | None = None
        self.weapons = dict()
        self.pre_move = list()
        self.post_move = list()
        self.errors = list()

    @property
    def all(self):
        all_cmds = [self.acceleration, self.turning, *self.weapons.values(), *self.pre_move, *self.post_move, *self.errors]
        return [e for e in all_cmds if e is not None]

    def add(self, cmd: Command):
        if not cmd.is_valid:
            print(str(cmd), 'not valid')
            self.errors.append(cmd)
            return
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
                self.weapons[cmd.selector] = cmd
            case Cmd.Activation:
                self.pre_move.append(cmd)
            case Cmd.Replenish | Cmd.Boost:
                self.post_move.append(cmd)
            case Cmd.Unknown:
                self.errors.append(cmd)
            case _:
                assert False, f"Unknown command: {cmd}"

    def __str__(self):
        wpn_str = 'W ' + '|'.join(f"{k}: {v}" for k, v in self.weapons.items()) if self.weapons else None
        pre_str = 'Pre ' + '|'.join([str(e) for e in self.pre_move]) if self.pre_move else None
        post_str = 'Post ' + '|'.join([str(e) for e in self.post_move]) if self.post_move else None
        unknown_str = 'Err ' + '|'.join([str(e) for e in self.errors]) if self.errors else None
        all_str = [str(e) for e in (self.acceleration, self.turning, wpn_str, pre_str, post_str, unknown_str) if e is not None]
        return f"CommandSet({', '.join(all_str)})"


class CommandValidator(object):
    def __init__(self, command: str, ship_type: str):
        pass


def read_command_file(command_file_name: str) -> dict:
    """Read a command file with the commands for a ship."""
    with open(command_file_name) as infile:
        logger.info(f"Reading {command_file_name}")
        lines = [line.strip() for line in infile.readlines() if not line.isspace()]

    commands = parse_commands(lines)
    logger.info(f"Parsed command file {command_file_name}")
    return commands


def parse_commands(lines: list[str]):
    commands = defaultdict(CommandSet)
    for line_nr, line in enumerate(lines, start=1):
        try:
            if line.startswith('#') or (line.strip() == ''):
                continue
            command_line = CommandLine(line)
            if command_line.is_valid:
                commands[command_line.tick].add(Command.for_command_line(command_line))
        except Exception:
            logger.error(f"Error while trying to parse line {line} ({line_nr})")
            raise
    return commands
