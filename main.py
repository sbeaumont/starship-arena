import logging

import command
from command import read_command_file
from log import configure_logger
from report import report_round
from ship import Ship
from shiptype import H2545
from history import History, ShipSnapshot
import pickle

logger = logging.getLogger(__name__)


def create_ship(line):
    name = line[0]
    xy = (int(line[1]), int(line[2]))
    ship = Ship(name, H2545(), xy)
    ship.history = History(ship, ShipSnapshot)
    return ship


def read_ship_file(file_name: str) -> list:
    """Load and initialize all the ships to their status at the start of a round."""
    ships = dict()
    with open(file_name) as infile:
        logger.info(f"Reading ship file {file_name}")
        lines = [line.strip().split(' ') for line in infile.readlines()]
        for line in lines:
            ship = create_ship(line)
            ships[ship.name] = ship
    return ships


def do_tick(objects_in_space: dict, destroyed: dict, tick: int):
    """Perform a single game tick."""
    logger.info(f"Processing tick {tick}")
    # Set up the reporting for the tick
    for ois in objects_in_space.values():
        ois.history.set_tick(tick)

    # Do all everything that has to happen before moving, then move each ship
    for ois in objects_in_space.values():
        ois.generate()
        if hasattr(ois, 'weapons'):
            for weapon in ois.weapons.values():
                weapon.tick(tick)
        if hasattr(ois, 'commands'):
            if tick in ois.commands:
                logger.info(f"Tick {tick} Ship {ois.name}: {str(ois.commands[tick])}")
                ois.commands[tick].pre_move_commands(ois)
            else:
                logger.info(f"Ship {ois.name} no commands this tick")
        ois.move()

    # After moving all ships scan and do post-move commands like firing weapons, and finally update the snapshot
    new_objects_in_space = list()
    for ois in objects_in_space.copy().values():
        if isinstance(ois, command.Commandable):
            if tick in ois.commands:
                new_objects = list()
                ois.commands[tick].post_move_commands(ois, objects_in_space, new_objects)
                for o in new_objects:
                    o.history.set_tick(tick)
        ois.scan(objects_in_space)
        ois.post_move(objects_in_space)
        ois.history.update()

    # Remove dead items
    for ois_name, ois in objects_in_space.copy().items():
        if ois.is_destroyed:
            logger.info(f"{ois_name} destroyed")
            destroyed[ois_name] = objects_in_space[ois_name]
            del objects_in_space[ois_name]


def do_round(ships: dict, destroyed: dict, game_dir: str, round_nr: int):
    """Execute a full round of 10 ticks."""
    for ship in ships.values():
        command_file_name = f"{game_dir}/{ship.name}-commands-{round_nr}.txt"
        ship.commands = read_command_file(command_file_name)
        ship.scan(ships)
    for i in range(1, 11):
        do_tick(ships, destroyed, i)


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
    report_round(objects_in_space, game_directory, game_round)
    report_round(destroyed, game_directory, game_round)

    for ois in objects_in_space.values():
        ois.round_reset()

    status_file_name = f'{game_directory}/status_turn_{game_round}.pickle'
    with open(status_file_name, 'wb') as status_file:
        pickle.dump(objects_in_space, status_file)


if __name__ == '__main__':
    configure_logger()
    main(1)
    main(2)

