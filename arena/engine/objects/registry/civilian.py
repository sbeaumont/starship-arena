"""Hulls nobody fights in. Which side may fly one is a scenario's table, never this file."""

from arena.cfg import max_scan
from arena.engine.objects.ship import ShipType
from arena.engine.objects.components.defense import Shields
from arena.engine.objects.components.ecm import Cloak
from arena.engine.objects.components.launcher import Launcher
from arena.engine.objects.registry.mines import EMPMine


class C2540(ShipType):
    """Slow, sharp on the helm, and armed with nothing that can take a hull down.

    The cloak draws at most twice the generators, which empties the battery in about eleven
    ticks: one round of running dark, and then it has to coast."""
    max_speed = 30
    max_turn = 60
    max_delta_v = 20
    max_hull = 90
    start_battery = 150
    generators = 10
    max_scan_distance = max_scan(25)

    @property
    def class_name(self):
        return "Envoy"

    @property
    def defense(self):
        return [
            Shields('Shields', {'N': 90, 'E': 90, 'S': 90, 'W': 90}),
        ]

    @property
    def ecm(self):
        return [
            Cloak('C1', 3),
        ]

    @property
    def weapons(self):
        return [
            Launcher('M1', EMPMine(), 6, (135, 225)),
        ]