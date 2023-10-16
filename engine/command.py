"""
The Command system allows players to control their ships (Command Pattern).

- Knows how to parse a command file and which command objects to instantiate for it
- All commands depend on the Commandable protocol which is implemented by ObjectInSpace
- Commands can be validated before they're executed, useful for the web interface (parse_commands).

Command objects:
- know how to retrieve Parameter objects from relevant Components and populate them.
- know how to specifically manipulate the object they're a command for.

CommandSet objects:
- holds all the commands of a player for one target ship for a specific tick.
- triggers its commands in the correct order within the tick.

The read_command_file function loads a command file and returns a dictionary (Tick, CommandSet). Wraps parse_commands.

The parse_commands is called by:
- the web interface (for validation)
- and the read_command_file (during the actual execution of the game engine)
"""

import re
import logging
from collections import defaultdict
from enum import Enum, auto
from typing import Protocol, runtime_checkable

from ois.objectinspace import ObjectInSpace
from ois.ship import AccelerationParameter, TurnParameter
from ois.comp.defense import Shields
from ois.comp.component import ComponentSelectorParameter
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
    """A single line (command) in a player's command file."""

    COMMAND_PATTERN = r"^(\d+):\s*([A-Za-z]+)((\s*-?[-\w]+)*)$"
    TICK_NAME_PARAMS = r"^(\d+):\s*([A-Za-z]+)(.*)$"

    def __init__(self, text: str):
        self.errors = list()
        self.text = text
        if self.is_valid:
            match = re.match(CommandLine.TICK_NAME_PARAMS, self.text)
            self.tick = int(match.group(1))
            self.name = match.group(2)
            self.params = [m for m in match.group(3).split(' ') if m.strip() != '']
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

    def fire(self, weapon_name: str, params: dict, objects_in_space: dict) -> ObjectInSpace:
        ...

    def try_replenish(self, objects_in_space: dict):
        ...

    def scan(self, objects_in_space: dict):
        ...

    def activation(self, name: str, on_off: bool):
        ...

    def add_event(self, event):
        ...

    def all_components(self):
        ...


class Command(object):
    @classmethod
    def for_command_line(cls, command_line: CommandLine, ship: Commandable, objects_in_space):
        match command_line.name.upper():
            case 'L' | 'R':
                # L90 -> Turn left
                return TurnCommand(command_line, ship, objects_in_space)
            case 'A':
                # A30 -> Accelerate faster (+) or slow down/reverse (-)
                return AccelerateCommand(command_line, ship, objects_in_space)
            case 'F' | 'FIRE' | 'SCAN':
                # Fire <Weapon Name> <Direction or Target name>
                return FireCommand(command_line, ship, objects_in_space)
            case 'REPLENISH':
                # Replenish
                return ReplenishCommand(command_line, ship, objects_in_space)
            case 'BOOST':
                # Boost shield quadrant
                return BoostCommand(command_line, ship, objects_in_space)
            case 'ACTIVATION' | 'ACTIVATE':
                # Turn components on or off
                return ActivationCommand(command_line, ship, objects_in_space)
            case _:
                logger.warning(f"Unknown command {command_line}")
                return UnknownCommand(command_line, ship, objects_in_space)

    def __init__(self, command_line: CommandLine, target: Commandable, objects_in_space):
        self.command_line = command_line
        self.ois = objects_in_space
        self.params = dict()
        self.feedback: list[str] = list()
        self.target = target
        params_valid = self._init_params(self.command_line.params)
        for fr in self.feedback_results:
            logger.info(f"{target.name} {fr}")
        self.is_valid = self.command_line.is_valid and params_valid

    def _init_params(self, params: list) -> bool:
        ...

    def _get_type_name(self) -> Cmd:
        ...

    @property
    def tick(self) -> int:
        return self.command_line.tick

    @property
    def name(self) -> Cmd:
        return self._get_type_name()

    @property
    def text(self) -> str:
        return self.command_line.text

    def execute(self, tick: int):
        logger.debug(f'{self.target.name} executing command "{self.command_line.text}"')
        self.target.add_event(InternalEvent(f'Executing command "{self.command_line.text}"'))

    @property
    def feedback_results(self):
        result = list()
        result.extend(self.feedback)
        for p in self.params.values():
            result.extend(p.feedback)
        return result

    def __repr__(self):
        return f"Command({self._get_type_name()}, {self.command_line})"


class ComponentCommand(Command):
    def __init__(self, command_line: CommandLine, target: Commandable, objects_in_space):
        self._selector = None
        super().__init__(command_line, target, objects_in_space)

    @property
    def feedback_results(self):
        result = super().feedback_results
        if self._selector:
            result.extend(self._selector.feedback)
        return result

    def init_selector(self, params: list) -> bool:
        if len(params) > 0:
            self._selector = ComponentSelectorParameter('selector', self.target, params[0])
            return self._selector.is_valid
        else:
            self.feedback.append(f"Expected parameters (component) (component parameters...)")
            return False

    @property
    def selector(self):
        assert self._selector is not None, f"{self} has no selector."
        return self._selector

    def _init_params(self, params: list) -> bool:
        if not self.init_selector(params):
            return False

        expected_parms = self.selector.value.expected_parameters
        nr_expected_parms = sum(p.number_of_inputs for p in expected_parms)
        input_params = params[1:]

        if len(input_params) != len(expected_parms):
            self.feedback.append(f"Expected {nr_expected_parms} parameters, got {len(input_params)}")
            return False

        i = 0
        for p in expected_parms:
            if p.needs_ois:
                p.set_ois(self.ois)
            if p.number_of_inputs > 1:
                p.input(input_params[i:i+p.number_of_inputs])
            else:
                p.input(input_params[i])
            self.params[p.name] = p
            i += p.number_of_inputs

        return all([p.is_valid for p in self.params.values()])


class AccelerateCommand(Command):
    def _init_params(self, params: list) -> bool:
        if len(params) == 1:
            p = AccelerationParameter('amount', self.target, params[0])
            self.params[p.name] = p
            return p.is_valid
        else:
            self.feedback.append(f"Expected 1 parameter, got {len(params)}")
            return False

    def _get_type_name(self) -> Cmd:
        return Cmd.Accelerate

    def execute(self, tick: int):
        super().execute(tick)
        self.target.accelerate(self.params['amount'].value)


class ActivationCommand(ComponentCommand):
    def _get_type_name(self) -> Cmd:
        return Cmd.Activation

    def execute(self, tick: int):
        super().execute(tick)
        self.target.activation(self.selector, self.params['on/off'].value)


class BoostCommand(Command):
    def _get_type_name(self) -> Cmd:
        return Cmd.Boost

    def _init_params(self, params: list) -> bool:
        for d in self.target.defense:
            if isinstance(d, Shields):
                self.component = d
                p = d.expected_parameters[0]
                p.input(params)
                self.params['boost'] = p
                break
        if 'boost' not in self.params:
            self.feedback.append(f"Can not find a Shield component.")
            return False
        return True

    def execute(self, tick: int):
        super().execute(tick)
        quadrant, amount = self.params['boost'].value
        self.component.boost(quadrant, int(amount))


class FireCommand(ComponentCommand):
    def _get_type_name(self) -> Cmd:
        return Cmd.Fire

    def execute(self, tick: int):
        super().execute(tick)
        weapon = self.selector.value
        fired_object = weapon.fire(self.params, self.ois)
        if fired_object:
            self.ois[fired_object.name] = fired_object


class ReplenishCommand(Command):
    def _init_params(self, params: list) -> bool:
        if len(params) > 0:
            self.feedback.append("Replenish command takes no arguments.")
            return False
        return True

    def _get_type_name(self) -> Cmd:
        return Cmd.Replenish

    def execute(self, tick: int):
        super().execute(tick)
        self.target.try_replenish(self.ois)


class TurnCommand(Command):
    def _init_params(self, params: list) -> bool:
        if len(params) == 1:
            p = TurnParameter('amount', self.target, params[0])
            self.params[p.name] = p
            return p.is_valid
        else:
            self.feedback.append(f"Expected 1 parameter, got {len(params)}")
            return False

    def _get_type_name(self) -> Cmd:
        return Cmd.Turn

    def execute(self, tick: int):
        super().execute(tick)
        angle = self.params['amount'].value
        angle = angle if self.command_line.name.upper() == 'R' else -angle
        self.target.turn(angle)


class UnknownCommand(Command):
    def __init__(self, command_line, target, objects_in_space):
        super().__init__(command_line, target, objects_in_space)
        self.feedback.append("Unknown command.")

    def _init_params(self, params: list) -> bool:
        return False

    def _get_type_name(self) -> Cmd:
        return Cmd.Unknown

    @property
    def is_valid(self) -> bool:
        # This command is never valid.
        return False

    @is_valid.setter
    def is_valid(self, value):
        pass

    def execute(self, tick: int):
        self.target.add_event(f"Can't execute unknown command {self.command_line.text}")


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
            logger.info(f"CommandSet: invalid command {str(cmd)}: {cmd.feedback_results}.")
            self.errors.append(cmd)
            return
        match cmd.name:
            case Cmd.Accelerate:
                self.acceleration = cmd
            case Cmd.Turn:
                self.turning = cmd
            case Cmd.Fire:
                self.weapons[cmd.selector.value] = cmd
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


def read_command_file(command_file_name: str, ship, objects_in_space) -> dict:
    """Read a command file with the commands for a ship."""
    with open(command_file_name) as infile:
        logger.info(f"Reading {command_file_name}")
        lines = [line.strip() for line in infile.readlines() if not line.isspace()]

    commands = parse_commands(lines, ship, objects_in_space)
    logger.info(f"Parsed command file {command_file_name}")
    return commands


def parse_commands(lines: list[str], ship, objects_in_space):
    commands = defaultdict(CommandSet)
    for line_nr, line in enumerate(lines, start=1):
        try:
            if line.startswith('#') or (line.strip() == ''):
                continue
            command_line = CommandLine(line)
            if command_line.is_valid:
                commands[command_line.tick].add(Command.for_command_line(command_line, ship, objects_in_space))
        except Exception:
            logger.error(f"Error while trying to parse line {line} ({line_nr})")
            raise
    return commands
