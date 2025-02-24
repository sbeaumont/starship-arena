from unittest import TestCase
from arena.engine import builder


class TestH2545(TestCase):
    def setUp(self) -> None:
        self.ois = {
            'TargetShip': builder.create("TargetShip", 'H2545', (0, 10)),
            'OwnerShip': builder.create("OwnerShip", 'H2545', (0, 100))
        }

    def test_weapons(self):
        self.ois['TargetShip'].weapons['M1'].status
