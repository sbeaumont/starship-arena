from unittest import TestCase
from .ois_fixtures import create_ship_fixture
from arena.engine.objects.objectinspace import Vector, Point
from arena.engine.history import TICK_ZERO
from arena.engine.objects.registry.missiles import Splinter


class TestMissile(TestCase):
    def setUp(self) -> None:
        self.ois = create_ship_fixture()
        self.missile = Splinter().create('TestSplinter', Vector(Point(0, 9), 0, 0), self.ois['OwnerShip'])

    def test_decide(self):
        tg = self.ois['TargetShip']
        self.missile.decide(self.ois)
        self.assertTrue(self.missile.is_destroyed)
        events = tg.history[TICK_ZERO].events
        self.assertEqual(len(events), 3)

    # def test__intercept(self):
    #     self.fail()
