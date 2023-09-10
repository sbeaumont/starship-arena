import logging
import os
import re
from pathlib import Path

from engine.admin import load_ship_file
from engine.command import parse_commands
from engine.gamedirectory import GameDirectory
from engine.round import GameRound
from secret import GAME_DATA_DIR
from ois.registry.builder import all_ship_types
from cfg import MANUAL_FILENAME

logger = logging.getLogger('starship-arena.facade')


class NameValidator(object):
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
    def __init__(self):
        self.data_root = Path(GAME_DATA_DIR)

    # ---------------------------------------------------------------------- QUERIES - Reference

    def get_turn_picture_name(self, game: str, ship_name: str, round: int) -> str:
        gd = GameDirectory(str(self.data_root), game)
        return gd.get_turn_picture_name(round, ship_name)

    def get_turn_pdf_name(self, game: str, ship_name: str, round: int) -> str:
        gd = GameDirectory(str(self.data_root), game)
        return gd.get_turn_pdf_name(round, ship_name)

    def get_manual_pdf(self) -> str:
        return MANUAL_FILENAME

    @property
    def all_ship_types(self) -> dict:
        return {st.__name__: st() for st in all_ship_types.values() if st.__name__ != 'SB2531'}

    @property
    def all_starbase_types(self) -> dict:
        return {'SB2531': all_ship_types['SB2531']()}

    # ---------------------------------------------------------------------- QUERIES - Game

    def all_games(self) -> list:
        return [os.path.basename(d) for d in self.data_root.iterdir() if d.is_dir()]

    def ships_for_game(self, game) -> list:
        gd = GameDirectory(str(self.data_root), game)
        return [s for s in gd.load_current_status().values() if s.is_player_controlled]

    def dead_ships_for_game(self, game) -> dict:
        gd = GameDirectory(str(self.data_root), game)
        return gd.load_graveyard()

    def current_round_of_game(self, game) -> int:
        gd = GameDirectory(str(self.data_root), game)
        return gd.last_round_number + 1

    def command_file_status_of_game(self, game) -> dict:
        gd = GameDirectory(str(self.data_root), game)
        ship_names = [s.name for s in self.ships_for_game(game)]
        round_nr = self.current_round_of_game(game)
        result = dict()
        for name in ship_names:
            result[name] = gd.command_file_exists(name, round_nr)
        return result

    def all_command_files_ok(self, game):
        return all(self.command_file_status_of_game(game).values())

    def get_last_commands(self, game, ship):
        round_nr = self.current_round_of_game(game)
        return self.commands_of_round(game, ship.name, round_nr)

    def get_ship(self, game: str, ship_name: str, round_nr=None):
        gd = GameDirectory(GAME_DATA_DIR, game)
        dead_ships = gd.load_graveyard()
        if round_nr > -1:
            if ship_name in dead_ships:
                return dead_ships[ship_name]
            else:
                return gd.load_status(round_nr)[ship_name]
        else:
            return gd.load_current_status()[ship_name]

    def commands_of_round(self, game: str, name: str, round_nr: int):
        gd = GameDirectory(str(self.data_root), game)
        if gd.command_file_exists(name, round_nr):
            with open(gd.command_file(name, round_nr)) as f:
                return [line.strip() for line in f.readlines()]
        else:
            return []

    # ---------------------------------------------------------------------- COMMANDS

    def check_commands(self, commands: list[str], ship_type) -> list[(bool, str)]:
        logger.debug(f"Commands to process: {commands}")
        parse_result = parse_commands(commands)
        commands = list()
        if parse_result:
            for t in sorted(parse_result.keys()):
                cs = parse_result[t]
                for c in cs.all:
                    commands.append([c.is_valid, c.command_line.text])
                logger.debug(f"Tick {t}: {str(cs)}")
        return commands

    def save_last_commands(self, game, ship, commands):
        gd = GameDirectory(str(self.data_root), game)
        round_nr = self.current_round_of_game(game)
        file_name = gd.command_file(ship, round_nr)
        logger.info(f"Writing G:{game} S:{ship} R:{round_nr} to {file_name}")
        with open(file_name, 'w') as f:
            f.write('\n'.join(commands))
            logger.debug(f"{commands} written to {file_name}")

    def process_turn(self, game):
        if self.all_command_files_ok(game):
            current_round = self.current_round_of_game(game)
            gd = GameDirectory(str(self.data_root), game)
            gr = GameRound(gd, current_round)
            logger.info(f"Processing round {current_round} of game {game}")
            gr.do_round()
        else:
            logger.info(f"Not proceeding to process {game}: not all command files ok")

    def create_new_game(self, name: str):
        logger.info(f"Creating new game: {name}")
