"""
This is the main processing engine.

GameRound processes a game turn.
1) It loads the previous round's status,
2) runs the round based on the players' command files,
3) saves the round's result and generates the output reports

Each tick has sub-phases where all objects get called in a specific ordering (see do_tick method).
"""
import logging

from arena.engine.command import Commandable, parse_commands, CommandSet
from arena.engine.gamedirectory import GameDirectory
from arena.engine.reporting.report import report_round
from .round import GameRound

logger = logging.getLogger('starship-arena.game')


class FilesMissing(Exception):
    """Raised when one or more files are missing."""


class Game(object):
    """The main processing engine of a game round."""
    def __init__(self, gd: GameDirectory):
        self._dir = gd
        self.rounds = dict()

    def init_round(self, round_nr) -> GameRound:
        """Initialize for the given round number."""
        if round_nr < 0 or round_nr > self.current_round_nr:
            raise ValueError(f"Round number has to be from 0 to {self.current_round_nr}, not {round_nr}.")
        # Initialize the - unprocessed - current round with the data from the previous round.
        round_to_load = round_nr if round_nr < self.current_round_nr else self.current_round_nr - 1
        return GameRound(self._dir.load_status(round_to_load), round_nr)

    def clear(self):
        self._dir.clean()

    # -------------------------------------------------------------------------------- Queries

    def get_round(self, round_nr: int) -> GameRound:
        if not round_nr in self.rounds:
            self.rounds[round_nr] = self.init_round(round_nr)
        return self.rounds[round_nr]

    @property
    def current_round(self) -> GameRound:
        return self.get_round(self.current_round_nr)

    @property
    def current_round_ready(self):
        """Return True if the current round is ready to run."""
        return not self.missing_command_files

    @property
    def current_round_nr(self):
        return self._dir.last_round_number + 1

    @property
    def missing_command_files(self) -> dict:
        missing = dict()
        for ship in self.player_ships:
            if not self._dir.command_file_exists(ship.name, self.current_round_nr):
                missing[ship.name] = self._dir.command_file(ship.name, self.current_round_nr)
        return missing

    @property
    def command_file_status(self) -> dict[str, bool]:
        return {ship.name: self._dir.command_file_exists(ship.name, self.current_round_nr) for ship in self.player_ships}

    @property
    def player_ships(self):
        """Return a list of all player controlled ships."""
        return [s for s in self.current_round.ois.values() if s.is_player_controlled]

    @property
    def factions(self):
        return {s.faction for s in self.player_ships}

    @property
    def players(self):
        return {s.player for s in self.player_ships}

    @property
    def name(self) -> str:
        return self._dir.game_name

    @property
    def graveyard(self):
        return self._dir.load_graveyard()

    # -------------------------------------------------------------------------------- Commands

    def process_current_round(self):
        """The main execution of the round. Here is where it all happens."""

        # Load all commands into player ships and do initial scan for reporting.
        if self.missing_command_files:
            raise FilesMissing(f"Missing command files {self.missing_command_files}")

        cr = self.current_round
        cr.do_round(self.load_commands())

        # Report the round
        report_round(cr.ois, self._dir, cr.round_nr)
        # ...incl. the final report of any player ships destroyed this round.
        if cr.destroyed:
            report_round(cr.destroyed, self._dir, cr.round_nr)
            self.update_graveyard(cr.destroyed.values())

        # Save the state of the current round.
        logger.debug(f"Saving game {self._dir.game_name} round {cr.round_nr}")
        self._dir.save(cr.ois, cr.round_nr)


    def load_commands(self):
        """Load the commands for the current round."""
        ship_commands = dict()
        for ship in [s for s in self.current_round.ois.values() if isinstance(s, Commandable)]:
            ship_commands[ship.name] = parse_commands(self._dir.read_command_file(ship.name,
                                                                                  self.current_round_nr),
                                                      ship,
                                                      self.current_round.ois)
        return ship_commands

    def update_graveyard(self, destroyed: list):
        """Update the graveyard with the ships passed as arguments."""
        graveyard = self.graveyard
        for dead_ship in [d for d in destroyed if d.is_player_controlled]:
            graveyard[dead_ship.name] = dead_ship
        self._dir.save_graveyard(graveyard)
