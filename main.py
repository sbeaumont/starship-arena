import argparse
import fnmatch
import logging
import os
import re
import pickle
import shutil
import sys
from collections import namedtuple

from cfg import *
from command import read_command_file, Commandable
from log import configure_logger
from ois import builder
from rep.report import report_round, report_round_zero
from rep.send import send_results_for_round

logger = logging.getLogger(__name__)
InitLine = namedtuple('InitLine', 'name type x y player')


class GameDirectory(object):
    def __init__(self, directory: str):
        self._dir = directory

        with open(self.init_file) as infile:
            logger.info(f"Reading ship file {self.init_file}")
            self.init_lines = list()
            for line in [l for l in infile.readlines() if l.strip()]:
                split_line = line.strip().split(' ')
                assert len(split_line) == 5, f"Expected {split_line} to have 5 elements"
                self.init_lines.append(InitLine(*split_line))

    @property
    def ls(self):
        return os.listdir(self._dir)

    @property
    def name(self):
        return self._dir

    @property
    def init_file(self):
        return os.path.join(self._dir, INIT_FILE_NAME)

    @property
    def last_round_number(self):
        last_round = -1
        pickle_files = fnmatch.filter(self.ls, '*.pickle')
        if len(pickle_files) > 0:
            last_round = max([int(n) for s in pickle_files for n in re.split('[-_. ]+', s) if n.isdigit()])
        return last_round

    def command_file(self, name, round_nr):
        return os.path.join(self._dir, COMMAND_FILE_TEMPLATE.format(name, round_nr))

    def status_file_for_round(self, nr):
        return os.path.join(self._dir, STATUS_FILE_TEMPLATE.format(nr))

    @property
    def last_status_file(self):
        return self.status_file_for_round(self.last_round_number)

    def clean(self, keep_pickle_files=False):
        """Clean the game directory of all generated files."""
        types_to_remove = ['*.html', '*.png', '*.pdf', '*.pickle']
        if keep_pickle_files:
            types_to_remove = types_to_remove[:-1]
        for file_type in types_to_remove:
            for f in fnmatch.filter(self.ls, file_type):
                os.remove(os.path.join(self._dir, f))

        # Remove round directories
        for rd_dir in fnmatch.filter(self.ls, 'round*'):
            shutil.rmtree(os.path.join(self._dir, rd_dir))


class RoundZero(object):
    def __init__(self, game_directory: GameDirectory):
        self._dir = game_directory
        self.ships = self._init_ships()

    def run(self):
        for ship in self.ships.values():
            ship.history.set_tick(0)
            ship.scan(self.ships)
            ship.history.update()
        report_round_zero(self._dir.name, self.ships.values())

    def _init_ships(self) -> dict:
        """Load and initialize all the ships to their status at the start of a round."""
        objects_in_space = dict()
        for line in self._dir.init_lines:
            position = (int(line.x), int(line.y))
            # Always for tick 0 in this case.
            ois = builder.create(line.name, line.type, position, 0)
            ois.player = line.player
            objects_in_space[ois.name] = ois
        return objects_in_space


class GameRound(object):
    def __init__(self, game_directory: GameDirectory, nr: int):
        assert nr > 0, "GameRound is only intended for rounds 1 and up."
        self._dir = game_directory
        self.nr = nr
        if self.nr == 1:
            self.objects_in_space = RoundZero(self._dir).ships
        else:
            old_status_file_name = self._dir.status_file_for_round(nr - 1)
            with open(old_status_file_name, 'rb') as old_status_file:
                self.objects_in_space = pickle.load(old_status_file)

    @property
    def ois(self):
        return self.objects_in_space

    def do_tick(self, destroyed: dict, tick: int):
        """Perform a single game tick."""
        logger.info(f"Processing tick {tick}")
        # Set up the reporting for the tick
        for ois in self.ois.values():
            ois.history.set_tick(tick)

        # Do everything that has to happen before moving, then move each ship
        for ois in self.ois.values():
            # Generate energy
            ois.generate()
            # Some weapons need to know a tick started, e.g. allowing a laser to cool every tick.
            # Or rocket launcher needing to know tick to create rockets with correct history.
            if hasattr(ois, 'weapons'):
                for weapon in ois.weapons.values():
                    weapon.tick(tick)
            # process all player pre-move commands (acceleration, turning)
            if isinstance(ois, Commandable) and ois.commands:
                if tick in ois.commands:
                    logger.info(f"Tick {tick} Ship {ois.name}: {str(ois.commands[tick])}")
                    ois.commands[tick].pre_move_commands(ois)
                else:
                    logger.info(f"Ship {ois.name} no commands this tick")
            # move ship
            ois.pre_move(self.objects_in_space)
            ois.move()

        # All ships perform their post move commands do post-move commands like firing weapons
        for ois in list(self.ois.values()):
            if isinstance(ois, Commandable) and ois.commands and (tick in ois.commands):
                ois.commands[tick].post_move_commands(ois, self.ois, tick)

        # All ships scan, do post-move logic (like guided missiles intercepting their target)
        # and finally update the snapshot
        for ois in list(self.ois.values()):
            ois.scan(self.ois)
            ois.post_move(self.ois)
            ois.history.update()

        # Remove dead items
        for ois_name, ois in self.ois.copy().items():
            if ois.is_destroyed:
                logger.info(f"{ois_name} destroyed")
                destroyed[ois_name] = self.ois[ois_name]
                del self.ois[ois_name]

    @property
    def missing_command_files(self):
        missing_command_files = list()
        for ship in [s for s in self.ois.values() if isinstance(s, Commandable)]:
            command_file_name = self._dir.command_file(ship.name, self.nr)
            if not os.path.exists(command_file_name):
                missing_command_files.append(command_file_name)
        return missing_command_files

    def do_round(self, exit_on_missing_command_file=True):
        # Execute the round
        destroyed = dict()
        # Load all commands into player ships and do initial scan for reporting.
        if exit_on_missing_command_file and self.missing_command_files:
            sys.exit(f"Missing command files {self.missing_command_files}")

        for ship in [s for s in self.ois.values() if isinstance(s, Commandable)]:
            command_file_name = self._dir.command_file(ship.name, self.nr)
            if os.path.exists(command_file_name):
                ship.commands = read_command_file(command_file_name)
                ship.scan(self.ois)

        # Do 10 ticks, 1-10
        for i in range(1, 11):
            self.do_tick(destroyed, i)

        # Report the round
        report_round(self.ois, self._dir.name, self.nr)
        # ...incl. the final report of any player ships destroyed this round.
        report_round(destroyed, self._dir.name, self.nr)

        self.save()

    def save(self):
        """Clean up unnecessary data from the objects and pickle them as starting point for the next round."""
        for ois in self.ois.values():
            ois.round_reset()
        status_file_name = self._dir.status_file_for_round(self.nr)
        with open(status_file_name, 'wb') as status_file:
            pickle.dump(self.ois, status_file)


def main():
    configure_logger(False, ["fontTools", "PIL"])
    parser = argparse.ArgumentParser()
    parser.add_argument("gamedir", help="The game directory you want to process.")
    parser.add_argument("round", choices=['zero', 'last', 'redo-all', 'none'], help="Which rounds to process")
    parser.add_argument("-y", "--yolo", action="store_true", help="Don't ask safety questions.")
    parser.add_argument("-c", "--clean", action="store_true", help="Clean the output files of a game directory")
    parser.add_argument("-i", "--ignore", action="store_true", help="Ignore missing command files.")
    parser.add_argument("-s", "--send", choices=['zero', 'last', 'all'], help="Send the results via email to the players")
    args = parser.parse_args()

    if not os.path.exists(args.gamedir):
        sys.exit(f"Game directory '{args.gamedir}' not found.")

    game_dir = GameDirectory(args.gamedir)
    last_round = game_dir.last_round_number

    if args.clean or (args.round == 'redo-all'):
        answer = None
        if not args.yolo:
            answer = input(f"Type 'Y' if you're sure you want to clean directory '{args.gamedir}'.\n")
        if args.yolo or (answer == 'Y'):
            game_dir.clean()

    def do_zero():
        init_file = game_dir.init_file
        if not os.path.exists(init_file):
            sys.exit(f"Can not find initialization file '{init_file}'")
        RoundZero(game_dir).run()

    match args.round:
        case 'zero':
            do_zero()
        case 'last':
            # Deal with last round ending up -1 if there's nothing.
            last_round = 1 if last_round == -1 else (last_round + 1)
            answer = None
            if not args.yolo:
                answer = input(f"Type 'Y' if you're sure you want to process new round '{last_round}'.\n")
            if args.yolo or (answer == 'Y'):
                gr = GameRound(game_dir, last_round)
                gr.do_round(not args.ignore)
        case 'redo-all':
            answer = None
            if not args.yolo:
                answer = input(f"Type 'Y' if you're sure you want to CLEAN AND REDO ALL.\n")
            if args.yolo or (answer == 'Y'):
                do_zero()
                round_nr = 1
                gr = GameRound(game_dir, round_nr)
                while not gr.missing_command_files:
                    # This will never be done with ignore missing command files, otherwise never stops.
                    gr.do_round()
                    round_nr += 1
                    gr = GameRound(game_dir, round_nr)
        case 'none':
            pass

    if args.send:
        answer = input(f"Type 'Y' to send out email.\n")
        if answer.upper() == 'Y':
            round_to_send = -1
            match args.send:
                case 'last':
                    round_to_send = last_round
                case 'zero':
                    round_to_send = 0
            if round_to_send > -1:
                send_results_for_round(game_dir.name, INIT_FILE_NAME, EMAIL_CFG_NAME, round_to_send)


if __name__ == '__main__':
    main()
