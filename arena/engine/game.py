"""Game is one game directory: which round it is on, whether the next one can run, and running it."""
import logging

from arena.engine.command import Commandable, parse_commands, CommandSet
from arena.engine.gamedirectory import GameDirectory
from arena.engine.history import Tick
from arena.engine.objects.registry import builder
from .round import GameRound
from .world import World

logger = logging.getLogger('starship-arena.game')


class FilesMissing(Exception):
    """Raised when one or more files are missing."""


class Game(object):
    """The main processing engine of a game round."""
    def __init__(self, gd: GameDirectory):
        self._dir = gd
        self.rounds = dict()
        # The latest world, until a round is initialised and replaces it with that round's.
        self.world = gd.load_current_world() or World(gd)

    def init_round(self, round_nr) -> GameRound:
        """Initialize for the given round number."""
        if round_nr < 0 or round_nr > self.current_round_nr:
            raise ValueError(f"Round number has to be from 0 to {self.current_round_nr}, not {round_nr}.")
        # Initialize the - unprocessed - current round with the data from the previous round.
        round_to_load = round_nr if round_nr < self.current_round_nr else self.current_round_nr - 1
        self.world = self._dir.load_world(round_to_load)
        self.plan_spawns(round_nr)
        return GameRound(self.world, round_nr)

    def plan_spawns(self, round_nr: int):
        """Put this round's lines of the spawn plan on the world, to arrive at their tick.

        The world is derived, so an arrival the director asked for lives in the plan or a
        regenerate would lose it. What a ShipSpawner creates is not there: its Fire order is
        the instruction, and a second record would spawn it twice."""
        for record in self._dir.load_spawns():
            if record['round'] == round_nr:
                self.world.plan_spawn(builder.from_plan(record, Tick(round_nr, record['tick'])))

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
        return [s for s in self.current_round.world.objects.values() if s.is_player_controlled]

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
        return self.world.graveyard

    # -------------------------------------------------------------------------------- Commands

    def process_current_round(self):
        """The main execution of the round. Here is where it all happens."""

        # Load all commands into player ships and do initial scan for reporting.
        if self.missing_command_files:
            raise FilesMissing(f"Missing command files {self.missing_command_files}")

        cr = self.current_round
        cr.do_round(self.load_commands())

        # Save the state of the current round.
        logger.debug(f"Saving game {self._dir.game_name} round {cr.round_nr}")
        cr.world.save(cr.round_nr)


    def load_commands(self):
        """Load the commands for the current round.

        Only a ship with a player has a command file. A hull with nobody at the helm still gets
        an entry, because its own Controller components may add commands as the round runs."""
        ship_commands = dict()
        for ship in [s for s in self.current_round.world.objects.values() if isinstance(s, Commandable)]:
            lines = self._dir.read_command_file(ship.name, self.current_round_nr) \
                if ship.is_player_controlled else []
            ship_commands[ship.name] = parse_commands(lines, ship, self.current_round.world)
        return ship_commands
