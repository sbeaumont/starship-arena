from unittest import TestCase
from .ois_fixtures import create_ship_fixture
from ois.objectinspace import Vector, Point
from rep.history import TICK_ZERO
from ois.registry.missiles import Splinter


class TestMissile(TestCase):
    def setUp(self) -> None:
        self.ois = create_ship_fixture()
        self.missile = Splinter().create('TestSplinter', Vector(Point(0, 9), 0, 0), self.ois['OwnerShip'])

    def test_post_move(self):
        tg = self.ois['TargetShip']
        self.missile.post_move(self.ois)
        self.assertTrue(self.missile.is_destroyed)
        events = tg.history[TICK_ZERO].events
        self.assertEqual(len(events), 3)

    # def test__intercept(self):
    #     self.fail()
