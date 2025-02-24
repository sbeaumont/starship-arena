from unittest import TestCase
from .ois_fixtures import create_ship_fixture
from arena.engine.objects.registry.mines import SplinterMine
from arena.engine import Vector, Point


class TestMine(TestCase):
    def setUp(self) -> None:
        self.ois = create_ship_fixture()
        self.mine = SplinterMine().create("TestMine", Vector(Point(0, 9), 0, 0), owner=self.ois['OwnerShip'], tick=1)

    def test_decide(self):
        self.mine.decide(self.ois)
        self.assertTrue(self.mine.is_destroyed)
