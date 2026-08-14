from arena.engine.objects.beacon import Beacon, BeaconType


class JumpPoint(BeaconType):
    """Where a ship leaves the system. Small, quiet, and it has to be found before it is reached."""
    base_type = Beacon
    radius = 5
    dock_range = 10
    max_approach_speed = 10

    # A full sweep of 346 picks this up at 138, so knowing roughly where it is buys a search
    # rather than a sighting. See docs/gddr/0031.
    visibility = 40