from arena.engine.objects.registry import builder
from arena.engine.world import World


def world_of(objects: dict, graveyard: dict = None) -> World:
    return World(objects, graveyard)


def create_ship_fixture():
    return {
        'TargetShip': builder.create("Target Ship", "H2545", (0, 10)),
        'OwnerShip': builder.create("Owner Ship", "H2552", (0, 100))
    }
