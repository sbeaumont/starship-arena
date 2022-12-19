import argparse
import fnmatch
import logging
import os
import re
import pickle
import sys
from collections import namedtuple

from command import read_command_file, Commandable
from log import configure_logger
from ois import shiptype
from rep.report import report_round, report_round_zero
from rep.email import send_results_for_round

logger = logging.getLogger(__name__)
InitLine = namedtuple('InitLine', 'name type x y player')


class GameDirectory(object):
    init_file_name = "ships.txt"
    email_cfg_name = "email.txt"
    status_file_template = "status_round_{}.pickle"
    command_file_template = "{}-commands-{}.txt"

    def __init__(self, directory: str):
        self._dir = directory

        with open(self.init_file) as infile:
            logger.info(f"Reading ship file {self.init_file}")
            self.init_lines = [InitLine(*line.strip().split(' ')) for line in infile.readlines()]

    @property
    def ls(self):
        return os.listdir(self._dir)

    @property
    def name(self):
        return self._dir

    @property
    def init_file(self):
        return os.path.join(self._dir, self.init_file_name)

    @property
    def last_round_number(self):
        last_round = -1
        pickle_files = fnmatch.filter(self.ls, '*.pickle')
        if len(pickle_files) > 0:
            last_round = max([int(n) for s in pickle_files for n in re.split('[-_. ]+', s) if n.isdigit()])
        return last_round

    def command_file(self, name, round):
        return os.path.join(self._dir, self.command_file_template.format(name, round))

    def status_file_for_round(self, nr):
        return os.path.join(self._dir, self.status_file_template.format(nr))

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


class RoundZero(object):
    def __init__(self, game_directory: GameDirectory):
        self._dir = game_directory
        self.ships = self._init_ships()

    def run(self):
        for ship in self.ships.values():
            ship.history.set_tick(0)
            ship.scan(self.ships)
        report_round_zero(self._dir.name, self.ships.values())

    def _init_ships(self) -> dict:
        """Load and initialize all the ships to their status at the start of a round."""
        objects_in_space = dict()
        for line in self._dir.init_lines:
            position = (int(line.x), int(line.y))
            # Always for tick 0 in this case.
            ois = shiptype.create(line.name, line.type, position, 0)
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
            ois.move()

        # After moving all ships scan and do post-move commands like firing weapons, and finally update the snapshot
        for ois in self.ois.copy().values():
            if isinstance(ois, Commandable) and ois.commands and (tick in ois.commands):
                new_objects = list()
                ois.commands[tick].post_move_commands(ois, self.ois, new_objects, tick)
            ois.scan(self.ois)
            ois.post_move(self.ois)
            ois.history.update()

        # Remove dead items
        for ois_name, ois in self.ois.copy().items():
            if ois.is_destroyed:
                logger.info(f"{ois_name} destroyed")
                destroyed[ois_name] = self.ois[ois_name]
                del self.ois[ois_name]

    def do_round(self, exit_on_missing_command_file=True):
        # Execute the round
        destroyed = dict()
        # Load all commands into player ships and do initial scan for reporting.
        missing_command_files = list()
        for ship in [s for s in self.ois.values() if isinstance(s, Commandable)]:
            command_file_name = self._dir.command_file(ship.name, self.nr)
            if os.path.exists(command_file_name):
                ship.commands = read_command_file(command_file_name)
                ship.scan(self.ois)
            else:
                missing_command_files.append(command_file_name)

        if exit_on_missing_command_file and missing_command_files:
            sys.exit(f"Missing command files {missing_command_files}")

        # Do 10 ticks, 1-10
        for i in range(1, 11):
            self.do_tick(destroyed, i)

        # Report the round
        report_round(self.ois, self._dir.name, self.nr)
        # ...incl. the final report of any player ships destroyed this round.
        report_round(destroyed, self._dir.name, self.nr)

        self.save()

    def save(self):
        # Clean up unnecessary data from the objects and pickle them as starting point for the next round.
        for ois in self.ois.values():
            ois.round_reset()
        status_file_name = self._dir.status_file_for_round(self.nr)
        with open(status_file_name, 'wb') as status_file:
            pickle.dump(self.ois, status_file)


def main():
    configure_logger(False, ["fontTools", "PIL"])
    parser = argparse.ArgumentParser()
    parser.add_argument("gamedir", help="The game directory you want to process.")
    parser.add_argument("-n", "--new", help="Initialize a new game in directory.", action="store_true")
    parser.add_argument("-i", "--ignore", help="Ignore missing command files.", action="store_true")
    parser.add_argument("--clean", help="Clean the output files of a game directory", action="store_true")
    parser.add_argument("-s", "--send", help="Send the results via email to the players", type=int, default=-1)
    args = parser.parse_args()

    if not os.path.exists(args.gamedir):
        sys.exit(f"Game directory '{args.gamedir}' not found.")

    game_dir = GameDirectory(args.gamedir)
    last_round = game_dir.last_round_number

    if args.send > -1:
        if (last_round > -1) and (0 <= args.send <= last_round):
            answer = input(f"Last round of {args.gamedir}: {last_round}. Type 'Y' to send round {args.send}.\n")
            if answer == 'Y':
                send_results_for_round(game_dir.name, game_dir.init_file_name, game_dir.email_cfg_name, args.send)
        else:
            sys.exit(f"No round {args.send} to send.")
    elif args.clean:
        answer = input(f"Type 'Y' if you're sure you want to clean directory '{args.gamedir}'.\n")
        if answer == 'Y':
            game_dir.clean()
    elif args.new:
        init_file = game_dir.init_file
        if not os.path.exists(init_file):
            sys.exit(f"Can not find initialization file '{init_file}'")
        # if (len(game_dir.ls) != 1) and (game_dir.ls[0] != game_dir.init_file_name):
        #     sys.exit(f"Expecting only one file '{game_dir.init_file_name}' in directory.")
        RoundZero(game_dir).run()
    else:
        # Deal with last round ending up -1 if there's nothing.
        new_round = 1 if last_round == -1 else (last_round + 1)
        answer = input(f"Type 'Y' if you're sure you want to process new round '{new_round}'.\n")
        if answer == 'Y':
            gr = GameRound(game_dir, new_round)
            gr.do_round(not args.ignore)


if __name__ == '__main__':
    main()
    # round_zero("./game")
    # do_round(1)
    # do_round(2)

