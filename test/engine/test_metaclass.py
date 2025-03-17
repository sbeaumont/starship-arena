import unittest

from abc import ABC, abstractmethod
from arena.engine.objects.registry.builder import _subclasses_recursive


class Weapon(object):
    power = 10

class ShipType(object):
    def initialize(self, ship):
        for k, v in self.attributes.items():
            setattr(ship, k, v)
        ship.weapons = self.weapons
        ship.class_name = self.name

    @property
    @abstractmethod
    def name(self):
        ...

    @property
    @abstractmethod
    def weapons(self) -> list:
        return list()

    @property
    @abstractmethod
    def attributes(self) -> dict:
        return dict()


class A2545(ShipType):
    @property
    def name(self):
        return 'Tiger'

    @property
    def attributes(self):
        result = super().attributes
        result.update({
            'a24': 20
        })
        return result

    @property
    def weapons(self):
        result = super().weapons
        result.extend([
            Weapon(),
        ])
        return result

builders = {st.__name__: st() for st in _subclasses_recursive(ShipType)}

class Ship(object):
    def __init__(self, ship_class):
        builders[ship_class].initialize(self)


class MyTestCase(unittest.TestCase):
    def test_something(self):
        # print("Creating MetaClass")
        # A2545 = ShipMetaClass('A2545', (Ship,), {})
        # print(f"Got a new class {A2545} with {dir(A2545)}")
        # print("Creating Ship")
        # ship = A2545()
        # print(f"Got a new Ship of type {type(ship)}", dir(ship))
        print(builders)
        ship = Ship('A2545')
        print(f"Got a new Ship of type {type(ship)}", dir(ship))
        print(ship.weapons[0].power)
        print(ship.class_name)
        print(ship.a24)



if __name__ == '__main__':
    unittest.main()
