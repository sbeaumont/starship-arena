import logging

import command
from command import read_command_file
from log import configure_logger
from report import report_round
from objectinspace import Ship
import shiptype
from history import History, ShipSnapshot
import pickle

logger = logging.getLogger(__name__)


def create_object_in_space(line):
    """Create an object based on a starting file line."""
    name = line[0]
    type_name = line[1]
    position = (int(line[2]), int(line[3]))
    # Always for tick 0 in this case.
    ois = shiptype.create(name, type_name, position, 0)
    return ois


def read_ship_file(file_name: str) -> list:
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
        # Or rocketlauncher needing to know tick to create rockets with correct history.
        if hasattr(ois, 'weapons'):
            for weapon in ois.weapons.values():
                weapon.tick(tick)
        # process all player pre-move commands (acceleration, turning)
        if hasattr(ois, 'commands'):
            if tick in ois.commands:
                logger.info(f"Tick {tick} Ship {ois.name}: {str(ois.commands[tick])}")
                ois.commands[tick].pre_move_commands(ois)
            else:
                logger.info(f"Ship {ois.name} no commands this tick")
        # move ship
        ois.move()

    # After moving all ships scan and do post-move commands like firing weapons, and finally update the snapshot
    for ois in objects_in_space.copy().values():
        if isinstance(ois, command.Commandable):
            if tick in ois.commands:
                new_objects = list()
                ois.commands[tick].post_move_commands(ois, objects_in_space, new_objects, tick)
                # for o in new_objects:
                #     o.history.set_tick(tick)
        ois.scan(objects_in_space)
        ois.post_move(objects_in_space)
        ois.history.update()

    # Remove dead items
    for ois_name, ois in objects_in_space.copy().items():
        if ois.is_destroyed:
            logger.info(f"{ois_name} destroyed")
            destroyed[ois_name] = objects_in_space[ois_name]
            del objects_in_space[ois_name]


def do_round(objects_in_space: dict, destroyed: dict, game_dir: str, round_nr: int):
    """Execute a full round of 10 ticks."""
    # Load all commands into player ships and do initial scan for reporting.
    for ship in [s for s in objects_in_space.values() if isinstance(s, Ship)]:
        command_file_name = f"{game_dir}/{ship.name}-commands-{round_nr}.txt"
        ship.commands = read_command_file(command_file_name)
        ship.scan(objects_in_space)
    # Do 10 ticks, 1-10
    for i in range(1, 11):
        do_tick(objects_in_space, destroyed, i)


def main(game_round: int):
    # Load initial data
    game_directory = "./game"
    if game_round == 1:
        objects_in_space = read_ship_file(f"{game_directory}/ships.txt")
    else:
        old_status_file_name = f'{game_directory}/status_turn_{game_round - 1}.pickle'
        with open(old_status_file_name, 'rb') as old_status_file:
            objects_in_space = pickle.load(old_status_file)

    # Execute the round
    destroyed = dict()
    do_round(objects_in_space, destroyed, game_directory, game_round)

    # Report the round
    report_round(objects_in_space, game_directory, game_round)
    # ...incl. the final report of any player ships destroyed this round.
    report_round(destroyed, game_directory, game_round)

    # Clean up unnecessary data from the objects and pickle them as starting point for the next round.
    for ois in objects_in_space.values():
        ois.round_reset()
    status_file_name = f'{game_directory}/status_turn_{game_round}.pickle'
    with open(status_file_name, 'wb') as status_file:
        pickle.dump(objects_in_space, status_file)


if __name__ == '__main__':
    configure_logger(False, ["fontTools", "PIL"])
    main(1)
    main(2)

