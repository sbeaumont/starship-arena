from arena.engine.objects.registry import builder
from arena.engine.world import World


def world_of(objects: dict, graveyard: dict = None) -> World:
    """A world for a unit test: nothing here saves itself, so it has no directory."""
    return World(None, objects, graveyard)


def create_ship_fixture():
    return {
        'TargetShip': builder.create("Target Ship", "H2545", (0, 10)),
        'OwnerShip': builder.create("Owner Ship", "H2552", (0, 100))
    }
