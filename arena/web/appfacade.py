"""
Facade that ensures that the flask_app file does not know too much about the internals like the database.

The AppFacade class may be a bit inconsistent: I simply added a method whenever I wanted to know or do something.
"""

import logging
import os
import re
from pathlib import Path

from arena.engine.admin import GameSetup
from arena.engine.command import parse_commands
from arena.engine.gamedirectory import GameDirectory, ShipFile
from arena.engine.game import Game
from secret import GAME_DATA_DIR
from arena.engine.objects.registry.builder import all_ship_types
from arena.engine.objects.ship import Ship
from arena.cfg import MANUAL_FILENAME

logger = logging.getLogger('starship-arena.facade')


class NameValidator(object):
    """Validation of ship names."""

    def __init__(self, name):
        self.name = name
        self.messages = list()

        self._check_correct_characters()
        self._check_not_empty()
        self._check_first_character_is_letter()

    @property
    def is_valid(self):
        return len(self.messages) == 0

    def _check_correct_characters(self):
        if not re.match(r'^[A-Za-z0-9\- ]+$', self.name):
            self.messages.append('Only letters, numbers, dashes and spaces in name.')

    def _check_first_character_is_letter(self):
        if not re.match(r'^[A-Za-z]', self.name):
            self.messages.append('First character must be a letter.')

    def _check_not_empty(self):
        if not self.name or len(self.name.strip()) == 0:
            self.messages.append('Name can not be empty.')

    @property
    def cleaned(self) -> str:
        return re.sub(r'\s', '_', self.name)


class AppFacade(object):
    """Object that hides specifics from the web interface."""

    def __init__(self):
        self.data_root = Path(GAME_DATA_DIR)

    def gd(self, game: str) -> GameDirectory:
        """To make the webapp more robust it initializes a game if it wasn't before returning."""
        gd = GameDirectory(str(self.data_root), game)
        if not gd.has_been_setup:
            logger.info(f"Setting up game {game}, since this was not done yet.")
            GameSetup(gd).execute()
        return gd

    def game(self, game_name: str) -> Game:
        return Game(self.gd(game_name))

    # ---------------------------------------------------------------------- QUERIES - Reference

    def get_turn_picture_name(self, game: str, ship_name: str, round_nr: int) -> str:
        return self.gd(game).get_turn_picture_name(round_nr, ship_name)

    def get_turn_pdf_name(self, game: str, ship_name: str, round_nr: int) -> str:
        return self.gd(game).get_turn_pdf_name(round_nr, ship_name)

    def get_manual_pdf(self) -> str:
        return MANUAL_FILENAME

    @property
    def all_ship_types(self) -> dict:
        return {st.__name__: st() for st in all_ship_types.values() if st.__name__ != 'SB2531'}

    @property
    def all_starbase_types(self) -> dict:
        return {'SB2531': all_ship_types['SB2531']()}

    # ---------------------------------------------------------------------- QUERIES - Game

    def all_game_names(self) -> list:
        return [os.path.basename(d) for d in self.data_root.iterdir() if d.is_dir()]

    def all_game_objs(self) -> list:
        return [self.game(name) for name in self.all_game_names()]

    def ships_for_game(self, game) -> list:
        return self.game(game).player_ships

    def dead_ships_for_game(self, game) -> dict:
        return self.gd(game).load_graveyard()

    def current_round_of_game(self, game) -> int:
        return self.gd(game).last_round_number + 1

    def all_command_files_ok(self, game):
        return all(self.command_file_status_of_game(game).values())

    def get_last_commands(self, game, ship_name):
        round_nr = self.current_round_of_game(game)
        return self.commands_of_round(game, ship_name, round_nr)

    def get_ship(self, game_name: str, ship_name: str, round_nr=None) -> Ship:
        gd = self.gd(game_name)
        dead_ships = gd.load_graveyard()
        if round_nr is not None and (round_nr > -1):
            if ship_name in dead_ships:
                return dead_ships[ship_name]
            else:
                return gd.load_status(round_nr)[ship_name]
        else:
            return gd.load_current_status()[ship_name]

    def commands_of_round(self, game: str, name: str, round_nr: int):
        gd = self.gd(game)
        if gd.command_file_exists(name, round_nr):
            return gd.read_command_file(name, round_nr)
        else:
            return []

    # ---------------------------------------------------------------------- COMMANDS

    def check_commands(self, game_name: str, ship_name: str, commands: list[str]) -> list[(bool, str)]:
        logger.debug(f"Checking commands for {game_name} {ship_name}: {commands}")
        ship = self.get_ship(game_name, ship_name)
        ois = self.gd(game_name).load_current_status()
        parse_result = parse_commands(commands, ship, ois)
        commands = list()
        if parse_result:
            for t in sorted(parse_result.keys()):
                cs = parse_result[t]
                for c in cs.all:
                    commands.append([c.is_valid, c.command_line.text, c.feedback_results])
                logger.debug(f"Tick {t}: {str(cs)}")
        return commands

    def save_last_commands(self, game, ship, commands):
        round_nr = self.current_round_of_game(game)
        file_name = self.gd(game).command_file(ship, round_nr)
        logger.info(f"Writing G:{game} S:{ship} R:{round_nr} to {file_name}")
        with open(file_name, 'w') as f:
            f.write('\n'.join(commands))
            logger.debug(f"{commands} written to {file_name}")

    def process_turn(self, game_name: str):
        game = Game(self.gd(game_name))
        if game.current_round_ready:
            logger.info(f"Processing round {game.current_round_nr} of game {game_name}")
            game.process_current_round()
        else:
            logger.info(f"Not proceeding to process {game_name}: not all command files ok")

    def create_new_game(self, name: str, ship_init_file: str):
        logger.info(f"Creating new game: {name}")

        gd = GameDirectory(str(self.data_root), name)
        if not gd.exists or not gd.has_been_setup:
            logger.info(f"Setting up game {name}, since this was not done yet.")
            ship_file = ShipFile(gd, ship_init_file)
            GameSetup(gd, ship_file).execute()
