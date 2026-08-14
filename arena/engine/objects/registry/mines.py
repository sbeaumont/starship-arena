from arena.engine.history import Tick, TICK_ZERO
from arena.engine.objects.components.warhead import (EMPWarhead, SplinterWarhead,
                                                     NanocyteWarhead)
from arena.engine.objects.machineinspace import MachineType
from arena.engine.objects.mine import Mine
from arena.engine.objects.geometry import Vector


class MineType(MachineType):
    slow_down_rate = 5
    energy_per_tick = 1
    max_speed = 0
    # Heavy for its size, so what it hits is felt. A casing with hull to spare rides out a drift
    # and goes off at anything faster.
    mass = 0.5

    def create(self, name: str, vector: Vector, owner=None, tick: Tick = TICK_ZERO):
        vector = vector.accelerate(-self.slow_down_rate)
        return super().create(name, vector, owner, tick)

    @property
    def max_scan_distance(self):
        return self.weapons[0].range


class SplinterMine(MineType):
    """The basic mine"""
    base_type = Mine
    max_battery = 50
    start_battery = 50
    max_hull = 5

    @property
    def weapons(self):
        return [
            SplinterWarhead('warhead'),
        ]


class EMPMine(MineType):
    """Takes the battery rather than the hull, so a pursuer loses its cloak and its speed."""
    base_type = Mine
    max_battery = 50
    start_battery = 50
    max_hull = 5

    @property
    def weapons(self):
        return [
            EMPWarhead('warhead'),
        ]


class NanocyteMine(MineType):
    """A mine that releases a cloud of nanocytes after exploding..."""
    base_type = Mine
    max_battery = 50
    start_battery = 50
    max_hull = 5

    @property
    def weapons(self):
        return [
            SplinterWarhead('warhead'),
            NanocyteWarhead('nanohead')
        ]
