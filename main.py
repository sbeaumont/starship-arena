import argparse
import fnmatch
import logging
import os
import re
import pickle
import sys

from command import read_command_file, Commandable
from log import configure_logger
from ois import shiptype
from rep.report import report_round, report_round_zero
from rep.email import send_results_for_round


logger = logging.getLogger(__name__)

INIT_FILE_NAME = "ships.txt"
STATUS_FILE_NAME = "status_round_{}.pickle"
EMAIL_CFG = "email.txt"


def create_object_in_space(line):
    """Create an object based on a starting file line."""
    name = line[0]
    type_name = line[1]
    position = (int(line[2]), int(line[3]))
    # Always for tick 0 in this case.
    ois = shiptype.create(name, type_name, position, 0)
    ois.player = line[4]
    return ois


def read_ship_file(file_name: str) -> dict:
    """Load and initialize all the ships to their status at the start of a round."""
    ships = dict()
    with open(file_name) as infile:
        logger.info(f"Reading ship file {file_name}")
        lines = [line.strip().split(' ') for line in infile.readlines()]
        for line in lines:
            ship = create_object_in_space(line)
            ships[ship.name] = ship
    return ships


def do_tick(objects_in_space: dict, destroyed: dict, tick: int):
    """Perform a single game tick."""
    logger.info(f"Processing tick {tick}")
    # Set up the reporting for the tick
    for ois in objects_in_space.values():
        ois.history.set_tick(tick)

    # Do everything that has to happen before moving, then move each ship
    for ois in objects_in_space.values():
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
    for ois in objects_in_space.copy().values():
        if isinstance(ois, Commandable) and ois.commands and (tick in ois.commands):
            new_objects = list()
            ois.commands[tick].post_move_commands(ois, objects_in_space, new_objects, tick)
        ois.scan(objects_in_space)
        ois.post_move(objects_in_space)
        ois.history.update()

    # Remove dead items
    for ois_name, ois in objects_in_space.copy().items():
        if ois.is_destroyed:
            logger.info(f"{ois_name} destroyed")
            destroyed[ois_name] = objects_in_space[ois_name]
            del objects_in_space[ois_name]


def do_round(game_round: int, exit_on_missing_command_file=True):
    # Load initial data
    game_directory = "./game"
    if game_round == 1:
        objects_in_space = read_ship_file(os.path.join(game_directory, INIT_FILE_NAME))
    else:
        old_status_file_name = os.path.join(game_directory, STATUS_FILE_NAME.format(game_round - 1))
        with open(old_status_file_name, 'rb') as old_status_file:
            objects_in_space = pickle.load(old_status_file)

    # Execute the round
    destroyed = dict()
    # Load all commands into player ships and do initial scan for reporting.
    missing_command_files = list()
    for ship in [s for s in objects_in_space.values() if isinstance(s, Commandable)]:
        command_file_name = os.path.join(game_directory, f"{ship.name}-commands-{game_round}.txt")
        if os.path.exists(command_file_name):
            ship.commands = read_command_file(command_file_name)
            ship.scan(objects_in_space)
        else:
            missing_command_files.append(command_file_name)

    if exit_on_missing_command_file and missing_command_files:
        sys.exit(f"Missing command files {missing_command_files}")

    # Do 10 ticks, 1-10
    for i in range(1, 11):
        do_tick(objects_in_space, destroyed, i)

    # Report the round
    report_round(objects_in_space, game_directory, game_round)
    # ...incl. the final report of any player ships destroyed this round.
    report_round(destroyed, game_directory, game_round)

    # Clean up unnecessary data from the objects and pickle them as starting point for the next round.
    for ois in objects_in_space.values():
        ois.round_reset()
    status_file_name = os.path.join(game_directory, STATUS_FILE_NAME.format(game_round))
    with open(status_file_name, 'wb') as status_file:
        pickle.dump(objects_in_space, status_file)


def round_zero(game_directory):
    ships = read_ship_file(os.path.join(game_directory, INIT_FILE_NAME))
    for ship in ships.values():
        ship.history.set_tick(0)
        ship.scan(ships)
    report_round_zero(game_directory, ships.values())


def clean(game_directory):
    gamedir_contents = os.listdir(game_directory)
    for file_type in ['*.html', '*.png', '*.pdf', '*.pickle']:
        for f in fnmatch.filter(gamedir_contents, file_type):
            os.remove(os.path.join(game_directory, f))


def last_round_number(gamedir):
    last_round = -1
    gamedir_contents = os.listdir(gamedir)
    pickle_files = fnmatch.filter(gamedir_contents, '*.pickle')
    if len(pickle_files) > 0:
        last_round = max([int(n) for s in pickle_files for n in re.split('[-_. ]+', s) if n.isdigit()])
    return last_round


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
    gamedir_contents = os.listdir(args.gamedir)
    last_round = last_round_number(args.gamedir)

    if args.send > -1:
        if (last_round > -1) and (0 <= args.send <= last_round):
            answer = input(f"Last round of {args.gamedir}: {last_round}. Type 'Y' to send round {args.send}.\n")
            if answer == 'Y':
                send_results_for_round(args.gamedir, INIT_FILE_NAME, EMAIL_CFG, args.send)
        else:
            sys.exit(f"No round {args.send} to send.")
    elif args.clean:
        answer = input(f"Type 'Y' if you're sure you want to clean directory '{args.gamedir}'.\n")
        if answer == 'Y':
            clean(args.gamedir)
    elif args.new:
        init_file = os.path.join(args.gamedir, INIT_FILE_NAME)
        if not os.path.exists(init_file):
            sys.exit(f"Can not find initialization file '{init_file}'")
        if (len(gamedir_contents) != 1) and (gamedir_contents[0] != INIT_FILE_NAME):
            sys.exit(f"Expecting only one file '{INIT_FILE_NAME}' in directory.")
        round_zero(args.gamedir)
    else:
        # Deal with last round ending up -1 if there's nothing.
        new_round = last_round + 1 if last_round >= 0 else 0
        answer = input(f"Type 'Y' if you're sure you want to process new round '{new_round}'.\n")
        if answer == 'Y':
            if new_round > 0:
                do_round(new_round, not args.ignore)
            else:
                round_zero(args.gamedir)


if __name__ == '__main__':
    main()
    # round_zero("./game")
    # do_round(1)
    # do_round(2)

