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
import sys

from engine.command import Commandable, parse_commands, CommandSet
from engine.gamedirectory import GameDirectory
from rep.report import report_round
from rep.history import Tick

logger = logging.getLogger('starship-arena.round')


class GameRound(object):
    """The main processing engine of a game round."""
    def __init__(self, gd: GameDirectory, round_nr: int):
        assert round_nr > 0, "GameRound is only intended for rounds 1 and up."
        self._dir = gd
        self.nr = round_nr
        self.round_start = Tick.for_start_of_round(self.nr)
        self.objects_in_space = self._dir.load_status(round_nr - 1)

    @property
    def ois(self):
        return self.objects_in_space

    def pre_move_commands(self, cs: CommandSet, tick: int):
        if cs.acceleration:
            cs.acceleration.execute(tick)
        if cs.turning:
            cs.turning.execute(tick)
        for cmd in cs.pre_move:
            cmd.execute(tick)

    def post_move_commands(self, cs: CommandSet, tick: int):
        for wpn_cmd in cs.weapons.values():
            wpn_cmd.execute(tick)
        for other_cmd in cs.post_move:
            other_cmd.execute(tick)

    def do_tick(self, destroyed: dict, tick: Tick):
        """Perform a single tick. This is where all hooks are called in the right order."""

        assert isinstance(tick, Tick)
        tick_nr = tick.abs_tick - tick.round_start.abs_tick + 1

        logger.info(f"Processing tick {tick}")
        # Set up the reporting for the tick
        for ois in self.ois.values():
            ois.history.set_tick(tick)
            ois.tick(tick)

        # Do everything that has to happen before moving, then move each ship
        for ois in self.ois.values():
            ois.generate()
            ois.use_energy()
            if isinstance(ois, Commandable) and ois.commands and (tick_nr in ois.commands):
                self.pre_move_commands(ois.commands[tick_nr], tick_nr)
            ois.pre_move(self.objects_in_space)
            ois.move()

        # All ships perform their post move commands do post-move commands like firing weapons
        for ois in list(self.ois.values()):
            if isinstance(ois, Commandable) and ois.commands and (tick_nr in ois.commands):
                self.post_move_commands(ois.commands[tick_nr], tick_nr)

        # All ships scan, "intelligent" objects make decisions (like guided missiles intercepting their target)
        for ois in list(self.ois.values()):
            ois.scan(self.ois)
            ois.decide(self.ois)

        # Perform post move steps like commands that perform at post move.
        # and finally update the snapshot
        for ois in list(self.ois.values()):
            ois.post_move(self.ois)
            ois.history.update()

        # Remove dead items
        for ois_name, ois in self.ois.copy().items():
            if ois.is_destroyed:
                logger.info(f"{ois_name} destroyed")
                destroyed[ois_name] = self.ois[ois_name]
                del self.ois[ois_name]

    @property
    def missing_command_files(self):
        missing_command_files = list()
        for ship in [s for s in self.ois.values() if isinstance(s, Commandable)]:
            if not self._dir.command_file_exists(ship.name, self.nr):
                missing_command_files.append(self._dir.command_file(ship.name, self.nr))
        return missing_command_files

    @property
    def is_generated(self):
        return os.path.exists(self._dir.status_file_for_round(self.nr))

    def do_round(self, exit_on_missing_command_file=True):
        """The main execution of the round. Here is where it all happens."""

        destroyed = dict()
        # Load all commands into player ships and do initial scan for reporting.
        if exit_on_missing_command_file and self.missing_command_files:
            sys.exit(f"Missing command files {self.missing_command_files}")

        for ois in self.ois.values():
            ois.round_reset()

        for ship in [s for s in self.ois.values() if isinstance(s, Commandable)]:
            ship.commands = parse_commands(self._dir.read_command_file(ship.name, self.nr), ship, self.ois)

        # Do 10 ticks, 1-10
        for t in self.round_start.ticks_for_round:
            self.do_tick(destroyed, t)

        for ois in self.ois.values():
            ois.post_round_reset()

        # Report the round
        report_round(self.ois, self._dir, self.nr)
        # ...incl. the final report of any player ships destroyed this round.
        if destroyed:
            report_round(destroyed, self._dir, self.nr)
            graveyard = self._dir.load_graveyard()
            for dead_ship in [d for d in destroyed.values() if d.is_player_controlled]:
                graveyard[dead_ship.name] = dead_ship
            self._dir.save_graveyard(graveyard)

        self.save()

    def save(self):
        self._dir.save(self.ois, self.nr)
