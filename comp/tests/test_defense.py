from unittest import TestCase

from ois.objectinspace import Vector, Point
from ois.machineinspace import MachineInSpace, MachineType
from ois.event import HitEvent
from ..warhead import DamageType

from ..defense import Shields


class DummyMachineType(MachineType):
    pass


class DummyContainer(MachineInSpace):
    def is_destroyed(self) -> bool:
        return False


class TestShields(TestCase):
    def create_container(self, name, x, y):
        vector = Vector(Point(x, y), 0, 0)
        return DummyContainer(name, DummyMachineType(), vector)

    def create_hit_event(self, damage_type, amount):
        return HitEvent(Point(0, 1),
                        damage_type,
                        self.attacker,
                        self.container,
                        amount)

    def setUp(self) -> None:
        self.shields = Shields('Shields', {'N': 100, 'E': 100, 'S': 100, 'W': 100})

        self.container = self.create_container('Dummy', 0, 0)
        self.shields.attach(self.container)

        self.owner = self.create_container('Owner', 10, 10)
        self.container.owner = self.owner

        self.attacker = self.create_container('Attacker', 0, 1)
        self.attacker.owner = self.create_container('Attacker Owner', 10, 11)

    def test_quadrant_of(self):
        def check(x, y):
            return self.shields.quadrant_of(Point(x, y))

        # North quadrant and edge cases
        self.assertEqual(check(0, 1), 'N')
        self.assertEqual(check(1, 1), 'N')
        self.assertEqual(check(-1, 1), 'N')
        self.assertEqual(check(100, 99), 'E')
        self.assertEqual(check(-100, 99), 'W')

        # Other quadrants
        self.assertEqual(check(0, -1), 'S')
        self.assertEqual(check(-1, 0), 'W')
        self.assertEqual(check(1, 0), 'E')

    def test_boost(self):
        self.container.battery = 300
        self.shields.boost('N', 300)
        self.assertEqual(self.shields.strengths['N'], 200)
        self.shields.take_damage_from(self.create_hit_event(DamageType.Explosion, 10))
        self.assertEqual(self.shields.strengths['N'], 190)
        self.shields.round_reset()
        self.assertEqual(self.shields.strengths['N'], 100)

    def test_take_damage_from_explosion(self):
        self.shields.take_damage_from(self.create_hit_event(DamageType.Explosion, 10))
        self.assertEqual(self.shields.strengths['N'], 90)
        self.shields.take_damage_from(self.create_hit_event(DamageType.Explosion, 10))
        self.assertEqual(self.shields.strengths['N'], 80)
        self.shields.take_damage_from(self.create_hit_event(DamageType.EMP, 10))
        self.assertEqual(self.shields.strengths['N'], 60)
        self.shields.take_damage_from(self.create_hit_event(DamageType.Nanocyte, 10))
        self.assertEqual(self.shields.strengths['N'], 60)

    def test_round_reset(self):
        self.container.battery = 300
        self.shields.boost('N', 300)
        self.shields.round_reset()
        self.assertEqual(self.shields.strengths['N'], 100)

