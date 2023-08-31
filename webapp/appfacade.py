import logging
import os
from pathlib import Path

from engine.command import parse_commands
from engine.gamedirectory import GameDirectory
from engine.round import GameRound
from secret import GAME_DATA_DIR
from ois.registry.builder import all_ship_types
from cfg import MANUAL_FILENAME

logger = logging.getLogger('starship-arena.facade')


class AppFacade(object):
    def __init__(self):
        self.data_root = Path(GAME_DATA_DIR)

    # ---------------------------------------------------------------------- QUERIES - Reference

    def get_turn_picture_name(self, game: str, ship_name: str, round: int):
        gd = GameDirectory(str(self.data_root), game)
        return gd.get_turn_picture_name(round, ship_name)

    def get_turn_pdf_name(self, game: str, ship_name: str, round: int):
        gd = GameDirectory(str(self.data_root), game)
        return gd.get_turn_pdf_name(round, ship_name)

    def get_manual_pdf(self):
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

    def current_round_of_game(self, game):
        gd = GameDirectory(str(self.data_root), game)
        return gd.last_round_number + 1

    def command_file_status_of_game(self, game):
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
        gd = GameDirectory(str(self.data_root), game)
        round_nr = self.current_round_of_game(game)
        if gd.command_file_exists(ship, round_nr):
            with open(gd.command_file(ship, round_nr)) as f:
                return [line.strip() for line in f.readlines()]
        else:
            return []

    def get_ship(self, game: str, ship_name: str, round_nr=None):
        gd = GameDirectory(GAME_DATA_DIR, game)
        if round_nr:
            status = gd.load_status(round_nr)
        else:
            status = gd.load_current_status()
        return status[ship_name]

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
        print(f"Writing {commands} to {file_name}")
        with open(file_name, 'w') as f:
            f.write('\n'.join(commands))

    def process_turn(self, game):
        if not self.all_command_files_ok(game):
            return
        gd = GameDirectory(str(self.data_root), game)
        gr = GameRound(gd, self.current_round_of_game(game))
        gr.do_round()
