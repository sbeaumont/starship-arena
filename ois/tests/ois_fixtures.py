from ois.ship import H2545, H2552


def create_ship_fixture():
    return {
        'TargetShip': H2545.create("Target Ship", (0, 10)),
        'OwnerShip': H2552.create("Owner Ship", (0, 100))
    }
