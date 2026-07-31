"""GameRound runs one round: ten ticks over the objects in space.

do_tick holds the phase order, which is the heart of the engine."""

import logging

from arena.engine.command import Commandable, CommandSet
from arena.engine.history import Tick
from arena.engine.world import World

logger = logging.getLogger('starship-arena.round')


class GameRound(object):
    """Takes the correct steps to process a game round."""
    def __init__(self, world: World, round_nr: int):
        self.world = world
        self.destroyed = dict()
        self.round_nr = round_nr

    def pre_move_commands(self, cs: CommandSet, tick: Tick):
        logger.debug(f"Pre-Move Commands @ tick {tick} for {cs}")
        if cs.acceleration:
            cs.acceleration.execute(tick)
        if cs.turning:
            cs.turning.execute(tick)
        for cmd in cs.pre_move:
            cmd.execute(tick)

    def post_move_commands(self, cs: CommandSet, tick: Tick):
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
        # Anything due this tick joins before the phases, so it lives the tick out in full.
        self.world.spawn(tick)

        # Set up the reporting for the tick
        for ois in self.world.objects.values():
            ois.history.set_tick(tick)
            ois.tick(tick)

        # Do everything that has to happen before moving, then move each ship
        for ois in self.world.objects.values():
            ois.generate()
            ois.use_energy()
            if isinstance(ois, Commandable) and ois.commands and (tick_nr in ois.commands):
                self.pre_move_commands(ois.commands[tick_nr], tick)
            ois.pre_move(self.world)
            ois.move()

        # All ships perform their post move commands do post-move commands like firing weapons
        for ois in list(self.world.objects.values()):
            if isinstance(ois, Commandable) and ois.commands and (tick_nr in ois.commands):
                self.post_move_commands(ois.commands[tick_nr], tick)

        # All ships scan, "intelligent" objects make decisions (like guided missiles intercepting their target)
        for ois in list(self.world.objects.values()):
            ois.scan(self.world)
            ois.decide(self.world, tick)

        # Perform post move steps like commands that perform at post move.
        # and finally update the snapshot
        for ois in list(self.world.objects.values()):
            ois.post_move(self.world)
            ois.history.update()

        # Clear the dead out, keeping the ones whose loss is worth a record.
        for ois_name, ois in self.world.objects.copy().items():
            if ois.is_destroyed:
                logger.info(f"{ois_name} destroyed")
                self.destroyed[ois_name] = ois
                if ois.leaves_a_wreck:
                    self.world.move_to_graveyard(ois)
                else:
                    self.world.remove(ois)

    def do_round(self, ship_commands: dict):
        """The main execution of the round. Here is where it all happens."""
        for ois in self.world.objects.values():
            ois.round_reset()

        for ship in [s for s in self.world.objects.values() if isinstance(s, Commandable)]:
            ship.commands = ship_commands[ship.name]

        # Do 10 ticks, 1-10
        round_start = Tick.for_start_of_round(self.round_nr)
        for t in round_start.ticks_for_round:
            self.do_tick(t)

        for ois in self.world.objects.values():
            ois.post_round_reset()
