from unittest import TestCase
from engine import builder


class TestH2545(TestCase):
    def setUp(self) -> None:
        self.ois = {
            'TargetShip': builder.create("TargetShip", 'H2545', (0, 10), 1),
            'OwnerShip': builder.create("OwnerShip", 'H2545', (0, 100), 1)
        }

    def test_weapons(self):
        self.ois['TargetShip'].weapons['M1'].status
