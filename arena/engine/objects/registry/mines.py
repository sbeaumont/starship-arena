from arena.engine.objects.components.warhead import SplinterWarhead, NanocyteWarhead
from arena.engine.objects.machineinspace import MachineType
from arena.engine.objects.mine import Mine
from arena.engine.objects.objectinspace import Vector


class MineType(MachineType):
    slow_down_rate = 5
    energy_per_tick = 1
    max_speed = 0

    def create(self, name: str, vector: Vector, owner=None, tick: int = 0):
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
    max_hull = 1

    @property
    def weapons(self):
        return [
            SplinterWarhead('warhead'),
        ]


class NanocyteMine(MineType):
    """A mine that releases a cloud of nanocytes after exploding..."""
    base_type = Mine
    max_battery = 50
    start_battery = 50
    max_hull = 1

    @property
    def weapons(self):
        return [
            SplinterWarhead('warhead'),
            NanocyteWarhead('nanohead')
        ]
