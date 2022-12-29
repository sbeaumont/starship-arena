from unittest import TestCase
from .ois_fixtures import create_ship_fixture
from ..registry.mines import SplinterMine


class TestMine(TestCase):
    def setUp(self) -> None:
        self.ois = create_ship_fixture()
        self.mine = SplinterMine.create("TestMine", (0, 0), 1, owner=self.ois['OwnerShip'])

    def test_post_move(self):
        self.mine.post_move(self.ois)
        self.assertTrue(self.mine.is_destroyed)
