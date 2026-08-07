from arena.engine.history import Tick
from arena.engine.objects.registry import builder
from arena.engine.round import GameRound
from arena.engine.world import World


def world_of(objects: dict, graveyard: dict = None) -> World:
    """A world for a unit test: nothing here saves itself, so it has no directory."""
    return World(None, objects, graveyard)


def run_ticks(world: World, how_many: int = 1, round_nr: int = 1):
    """Run whole ticks over a world.

    Movement, what anything runs into and what any warhead goes off on are one loop now, so a
    test that moves an object by hand is testing a tick that does not exist.
    See docs/adr/0023-a-tick-advances-by-encounters.md."""
    game_round = GameRound(world, round_nr)
    for tick in Tick.for_start_of_round(round_nr).ticks_for_round[:how_many]:
        game_round.do_tick(tick)


def create_ship_fixture():
    """Two ships on opposite sides, so what one of them fires has something to go off on."""
    target = builder.create("Target Ship", "H2545", (0, 10))
    target.faction = 'Them'
    owner = builder.create("Owner Ship", "H2552", (0, 100))
    owner.faction = 'Us'
    return {'TargetShip': target, 'OwnerShip': owner}
