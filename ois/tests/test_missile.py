from unittest import TestCase
from .ois_fixtures import create_ship_fixture
from ..registry.missiles import Splinter


class TestMissile(TestCase):
    def setUp(self) -> None:
        self.ois = create_ship_fixture()
        self.missile = Splinter.create('TestSplinter', (0, 9), self.ois['OwnerShip'])

    def test_post_move(self):
        tg = self.ois['TargetShip']
        self.missile.post_move(self.ois)
        self.assertTrue(self.missile.is_destroyed)
        events = tg.history[1].events
        self.assertEquals(len(events), 3)

    # def test__intercept(self):
    #     self.fail()
