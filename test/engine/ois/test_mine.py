from unittest import TestCase

from arena.engine.history import TICK_ZERO
from arena.engine.objects.geometry import Point, Vector
from arena.engine.objects.registry.mines import SplinterMine

from .ois_fixtures import create_ship_fixture, run_ticks, world_of


class TestMine(TestCase):
    def setUp(self) -> None:
        self.ois = create_ship_fixture()
        self.mine = SplinterMine().create("TestMine", Vector(Point(0, 9), 0, 0),
                                          owner=self.ois['OwnerShip'], tick=TICK_ZERO)
        self.ois['TestMine'] = self.mine
        self.world = world_of(self.ois)

    def test_it_goes_off_on_something_that_comes_within_range(self):
        """Laid a unit off TargetShip at (0, 10), well inside a SplinterWarhead's 6."""
        run_ticks(self.world)

        self.assertTrue(self.mine.is_destroyed)
