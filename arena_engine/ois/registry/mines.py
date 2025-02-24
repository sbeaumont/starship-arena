from arena_engine.ois.comp.warhead import SplinterWarhead, NanocyteWarhead
from arena_engine.ois.machineinspace import MachineType
from arena_engine.ois.mine import Mine
from arena_engine.ois.objectinspace import Vector


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
