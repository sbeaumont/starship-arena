"""
This is the main processing engine.

GameRound processes a game turn.
1) It loads the previous round's status,
2) runs the round based on the players' command files,
3) saves the round's result and generates the output reports

Each tick has sub-phases where all objects get called in a specific ordering (see do_tick method).
"""

import os
import logging

from arena.engine.command import Commandable, parse_commands, CommandSet
from arena.engine.gamedirectory import GameDirectory
from arena.engine.reporting.report import report_round
from arena.engine.history import Tick
from .round import GameRound

logger = logging.getLogger('starship-arena.round')


class FilesMissing(Exception):
    """Raised when one or more files are missing."""


class Game(object):
    """The main processing engine of a game round."""
    def __init__(self, gd: GameDirectory):
        self._dir = gd
        self.round_nr = 1 if self._dir.last_round_number == 0 else self._dir.last_round_number
        self.init_round(self.round_nr)

    def init_round(self, round_nr):
        """Initialize for the given round number."""
        if round_nr < 1:
            raise ValueError("GameRound is only intended for rounds 1 and up.")
        self.round_nr = round_nr
        self.round_start = Tick.for_start_of_round(self.round_nr)
        self.ois = self._dir.load_status(round_nr - 1)

    def init_next_round(self):
        """Initialize for the next round."""
        self.init_round(self.round_nr + 1)

    # -------------------------------------------------------------------------------- Queries

    @property
    def round_ready(self):
        """Return True if the current round is ready to run."""
        return not self.is_generated and not self.missing_command_files

    @property
    def is_generated(self):
        return self._dir.status_file_for_round_exists(self.round_nr)

    @property
    def missing_command_files(self):
        missing_command_files = list()
        for ship in [s for s in self.ois.values() if isinstance(s, Commandable)]:
            if not self._dir.command_file_exists(ship.name, self.round_nr):
                missing_command_files.append(self._dir.command_file(ship.name, self.round_nr))
        return missing_command_files

    # -------------------------------------------------------------------------------- Commands

    def do_round(self):
        """The main execution of the round. Here is where it all happens."""

        # Load all commands into player ships and do initial scan for reporting.
        if self.missing_command_files:
            raise FilesMissing(f"Missing command files {self.missing_command_files}")

        game_round = GameRound(self.ois)
        game_round.do_round(self.load_commands(), self.round_nr)

        # Report the round
        report_round(self.ois, self._dir, self.round_nr)
        # ...incl. the final report of any player ships destroyed this round.
        if game_round.destroyed:
            report_round(game_round.destroyed, self._dir, self.round_nr)
            self.update_graveyard(game_round.destroyed.values())

        self.save()

    def load_commands(self):
        """Load the commands for the current round."""
        ship_commands = dict()
        for ship in [s for s in self.ois.values() if isinstance(s, Commandable)]:
            ship_commands[ship.name] = parse_commands(self._dir.read_command_file(ship.name, self.round_nr), ship, self.ois)
        return ship_commands

    def update_graveyard(self, destroyed: list):
        """Update the graveyard with the ships passed as arguments."""
        graveyard = self._dir.load_graveyard()
        for dead_ship in [d for d in destroyed if d.is_player_controlled]:
            graveyard[dead_ship.name] = dead_ship
        self._dir.save_graveyard(graveyard)

    def save(self):
        """Save the state of the current round."""
        self._dir.save(self.ois, self.round_nr)
