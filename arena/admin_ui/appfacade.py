"""
Facade that keeps the director's console from knowing too much about the internals.

It is the semantic layer for this one UI: everything the console asks about a game, in the
console's own terms. Player-facing operations live in the application-services layer instead.
"""

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

from arena.app.dto import GameSettings
from arena.app.services import AdminService
from arena.engine.admin import GameSetup, regenerate_game
from arena.engine.gamedirectory import GameDirectory, ShipFile
from arena.engine.game import Game
from arena.cfg import GAME_DATA_DIR, MANUAL_FILENAME
from arena.engine.objects.registry.builder import all_ship_types
from arena.engine.objects.starbase import Starbase

logger = logging.getLogger('starship-arena.facade')


class NameValidator(object):
    """Validation of ship names."""

    def __init__(self, name):
        self.name = name
        self.messages = list()

        self._check_not_empty()
        # The other two have nothing to say about a name that isn't there, and saying it anyway
        # buries the one message that matters under two that don't.
        if self.name and self.name.strip():
            self._check_correct_characters()
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


@dataclass
class GameLine:
    """One game as the director's console shows it: is this round ready, and if not, who is owed.

    `ready` is the engine's own verdict rather than something derived here, so there is only ever
    one definition of a round being ready to process."""
    name: str
    round_nr: int
    ships: int
    orders_in: int
    missing: list[str]
    ready: bool
    players: int
    players_ready: int
    not_ready: list[str]

    @property
    def percent_in(self) -> int:
        return round(100 * self.orders_in / self.ships) if self.ships else 0

    @property
    def all_ready(self) -> bool:
        return bool(self.players) and self.players_ready == self.players


class AppFacade(object):
    """Object that hides specifics from the web interface."""

    def __init__(self):
        self.data_root = Path(GAME_DATA_DIR)
        self.admin = AdminService(self.data_root)

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

    def get_manual_pdf(self) -> str:
        return MANUAL_FILENAME

    # The registry holds ready-made type instances, keyed by type name. Which of them are
    # starbases is decided by the type itself, not by naming the one we happen to have.
    @property
    def all_ship_types(self) -> dict:
        return {name: st for name, st in all_ship_types.items() if not issubclass(st.base_type, Starbase)}

    @property
    def all_starbase_types(self) -> dict:
        return {name: st for name, st in all_ship_types.items() if issubclass(st.base_type, Starbase)}

    # ---------------------------------------------------------------------- QUERIES - Game

    def all_game_names(self) -> list:
        return [os.path.basename(d) for d in self.data_root.iterdir() if d.is_dir()]

    def all_game_objs(self) -> list:
        return [self.game(name) for name in self.all_game_names()]

    def game_lines(self) -> list[GameLine]:
        lines = []
        for game in self.all_game_objs():
            status = game.command_file_status
            players = sorted(p for p in game.players if p)
            said_ready = [p for p in players if self.admin.is_ready(game.name, p)]
            lines.append(GameLine(name=game.name,
                                  round_nr=game.current_round_nr,
                                  ships=len(status),
                                  orders_in=sum(1 for ok in status.values() if ok),
                                  missing=sorted(n for n, ok in status.items() if not ok),
                                  ready=game.current_round_ready,
                                  players=len(players),
                                  players_ready=len(said_ready),
                                  not_ready=[p for p in players if p not in said_ready]))
        return lines

    # ---------------------------------------------------------------------- COMMANDS

    def process_turn(self, game_name: str):
        game = Game(self.gd(game_name))
        if game.current_round_ready:
            logger.info(f"Processing round {game.current_round_nr} of game {game_name}")
            game.process_current_round()
        else:
            logger.info(f"Not proceeding to process {game_name}: not all command files ok")

    def regenerate_game(self, game_name: str) -> int:
        return regenerate_game(self.gd(game_name))

    def is_ready(self, game: str, player: str) -> bool:
        return self.admin.is_ready(game, player)

    def settings(self, game: str):
        return self.admin.settings(game)

    def save_settings(self, game: str, on_all_ready: bool, hours: list[int]) -> None:
        self.admin.save_settings(game, GameSettings(on_all_ready=on_all_ready, process_hours=hours))

    def archived_games(self) -> list:
        return self.admin.list_archived_games()

    def archive_game(self, name: str) -> None:
        self.admin.archive_game(name)

    def unarchive_game(self, name: str) -> None:
        self.admin.unarchive_game(name)

    def delete_archived_game(self, name: str) -> None:
        self.admin.delete_archived_game(name)

    # ---------------------------------------------------------------------- LOGINS

    def player_holding(self, token: str):
        """Who this token belongs to, or None. The console is the director's, so callers check
        `is_director` rather than merely that somebody answered."""
        return self.admin.players.by_token(token)

    def logins(self) -> list:
        return self.admin.logins()

    def issue_login(self, name: str, director: bool = False):
        return self.admin.issue_login(name, director)

    def revoke_login(self, name: str) -> None:
        self.admin.revoke_login(name)

    def create_new_game(self, name: str, ship_init_file: str):
        logger.info(f"Creating new game: {name}")

        gd = GameDirectory(str(self.data_root), name)
        if not gd.exists or not gd.has_been_setup:
            logger.info(f"Setting up game {name}, since this was not done yet.")
            ship_file = ShipFile(gd, ship_init_file)
            GameSetup(gd, ship_file).execute()
