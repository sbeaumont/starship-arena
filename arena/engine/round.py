"""
This is the main processing engine.

GameRound processes a game turn.
1) It loads the previous round's status,
2) runs the round based on the players' command files,
3) saves the round's result and generates the output reports

Each tick has sub-phases where all objects get called in a specific ordering (see do_tick method).
"""

import logging

from arena.engine.command import Commandable, CommandSet
from arena.engine.history import Tick

logger = logging.getLogger('starship-arena.round')


class GameRound(object):
    """Takes the correct steps to process a game round."""
    def __init__(self, objects_in_space: dict, round_nr: int):
        self.ois = objects_in_space
        self.destroyed = dict()
        self.round_nr = round_nr

    def pre_move_commands(self, cs: CommandSet, tick: int):
        logger.debug(f"Pre-Move Commands @ tick {tick} for {cs}")
        if cs.acceleration:
            cs.acceleration.execute(tick)
        if cs.turning:
            cs.turning.execute(tick)
        for cmd in cs.pre_move:
            cmd.execute(tick)

    def post_move_commands(self, cs: CommandSet, tick: int):
        logger.debug(f"Post-Move Commands @ tick {tick} for {cs}")
        for wpn_cmd in cs.weapons.values():
            wpn_cmd.execute(tick)
        for other_cmd in cs.post_move:
            other_cmd.execute(tick)

    def do_tick(self, tick: Tick):
        """Perform a single tick. This is where all hooks are called in the right order."""
        logger.debug(f"Starting tick: {tick}")
        if not isinstance(tick, Tick):
            raise TypeError("tick must be of type Tick")

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
            ois.pre_move(self.ois)
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
                self.destroyed[ois_name] = self.ois[ois_name]
                del self.ois[ois_name]

    def do_round(self, ship_commands: dict):
        """The main execution of the round. Here is where it all happens."""
        for ois in self.ois.values():
            ois.round_reset()

        for ship in [s for s in self.ois.values() if isinstance(s, Commandable)]:
            ship.commands = ship_commands[ship.name]

        # Do 10 ticks, 1-10
        round_start = Tick.for_start_of_round(self.round_nr)
        for t in round_start.ticks_for_round:
            self.do_tick(t)

        for ois in self.ois.values():
            ois.post_round_reset()
