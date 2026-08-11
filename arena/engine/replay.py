"""A game as it was played, for reading rather than for running.

Game is the game moving forward. This is every round of it that has been saved, so any tick can be
asked what was in space at it."""

from arena.engine.gamedirectory import GameDirectory
from arena.engine.history import TICK_ZERO, Tick
from arena.engine.world import World


class Replay(object):
    """Every saved round of a game, keyed by round number.

    A world holds each object's history up to the round it was saved on, so the world that knows
    about a tick is the one saved for that tick's round. Ask an earlier one and the tick is not
    there yet; ask a later one and its copy of the object has moved on."""

    def __init__(self, gd: GameDirectory):
        self.worlds = {nr: gd.load_world(nr) for nr in range(gd.last_round_number + 1)}

    @property
    def first(self) -> Tick:
        """The setup state, which is where every game's timeline opens."""
        return TICK_ZERO

    @property
    def last(self) -> Tick:
        return Tick(max(self.worlds), 10)

    @property
    def ticks(self) -> list[Tick]:
        """Every tick the game has played, in order. What a playhead scrubs over."""
        return [Tick.from_abs(a) for a in range(self.first.abs_tick, self.last.abs_tick + 1)]

    def world_at(self, tick: Tick) -> World:
        return self.worlds[tick.round]

    def objects_at(self, tick: Tick) -> dict:
        """What was in space at that tick, by name.

        Being there is having a snapshot for the tick, which is the whole of it: something that
        arrived later has nothing before it, and anything destroyed stops answering at the tick it
        died on. What the round killed is read beside what survived it, since a rocket that goes
        off is in neither the objects nor the graveyard."""
        world = self.world_at(tick)
        return {name: ois for name, ois in (world.objects | world.destroyed).items()
                if tick in ois.history}