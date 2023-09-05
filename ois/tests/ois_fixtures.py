from ois.registry import builder


def create_ship_fixture():
    return {
        'TargetShip': builder.create("Target Ship", "H2545" , (0, 10)),
        'OwnerShip': builder.create("Owner Ship", "H2552", (0, 100))
    }
