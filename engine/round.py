import os
import pickle
import logging
import sys

from engine.command import Commandable, read_command_file, CommandSet
from engine.gamedirectory import GameDirectory
from rep.report import report_round
from rep.history import Tick

logger = logging.getLogger('starship-arena.round')


class GameRound(object):
    def __init__(self, gd: GameDirectory, round_nr: int):
        assert round_nr > 0, "GameRound is only intended for rounds 1 and up."
        self._dir = gd
        self.nr = round_nr
        self.round_start = Tick(self.nr, 0)
        old_status_file_name = self._dir.status_file_for_round(round_nr - 1)
        if os.path.exists(old_status_file_name):
            with open(old_status_file_name, 'rb') as old_status_file:
                self.objects_in_space = pickle.load(old_status_file)
        else:
            raise Exception(f"Can't find status file {old_status_file_name}")

    @property
    def ois(self):
        return self.objects_in_space

    def pre_move_commands(self, ship: Commandable, cs: CommandSet, tick: int):
        if cs.acceleration:
            cs.acceleration.execute(ship, self.ois, tick)
        if cs.turning:
            cs.turning.execute(ship, self.ois, tick)
        for cmd in cs.pre_move:
            cmd.execute(ship, self.ois, tick)

    def post_move_commands(self, ship: Commandable, cs: CommandSet, objects_in_space: dict, tick: int):
        for wpn_cmd in cs.weapons.values():
            wpn_cmd.execute(ship, self.ois, tick)
        for other_cmd in cs.post_move:
            other_cmd.execute(ship, self.ois, tick)

    def do_tick(self, destroyed: dict, tick: Tick):
        assert isinstance(tick, Tick)
        tick_nr = tick.abs_tick - tick.round_start.abs_tick + 1
        """Perform a single game tick."""
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
                self.pre_move_commands(ois, ois.commands[tick_nr], tick_nr)
            ois.pre_move(self.objects_in_space)
            ois.move()

        # All ships perform their post move commands do post-move commands like firing weapons
        for ois in list(self.ois.values()):
            if isinstance(ois, Commandable) and ois.commands and (tick_nr in ois.commands):
                self.post_move_commands(ois, ois.commands[tick_nr], self.ois, tick_nr)

        # All ships scan, do post-move logic (like guided missiles intercepting their target)
        # and finally update the snapshot
        for ois in list(self.ois.values()):
            ois.scan(self.ois)
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
            command_file_name = self._dir.command_file(ship.name, self.nr)
            if not os.path.exists(command_file_name):
                missing_command_files.append(command_file_name)
        return missing_command_files

    @property
    def is_generated(self):
        return os.path.exists(self._dir.status_file_for_round(self.nr))

    def do_round(self, exit_on_missing_command_file=True):
        # Execute the round
        destroyed = dict()
        # Load all commands into player ships and do initial scan for reporting.
        if exit_on_missing_command_file and self.missing_command_files:
            sys.exit(f"Missing command files {self.missing_command_files}")

        for ois in self.ois.values():
            ois.round_reset()

        for ship in [s for s in self.ois.values() if isinstance(s, Commandable)]:
            command_file_name = self._dir.command_file(ship.name, self.nr)
            if os.path.exists(command_file_name):
                ship.commands = read_command_file(command_file_name)
                # ship.scan(self.ois)

        # Do 10 ticks, 1-10
        for t in self.round_start.ticks_for_round:
            self.do_tick(destroyed, t)

        # Report the round
        report_round(self.ois, self._dir.path, self.nr)
        # ...incl. the final report of any player ships destroyed this round.
        report_round(destroyed, self._dir.path, self.nr)

        self.save()

    def save(self):
        self._dir.save(self.ois, self.nr)
