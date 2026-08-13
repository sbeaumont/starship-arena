from unittest import TestCase

from arena.engine.objects.registry import builder
from arena.engine.objects.registry.mines import SplinterMine
from arena.engine.objects.registry.missiles import Rocket
from arena.engine.objects.geometry import Point, Vector


class TestH2545(TestCase):
    def setUp(self) -> None:
        self.ois = {
            'TargetShip': builder.create("TargetShip", 'H2545', (0, 10)),
            'OwnerShip': builder.create("OwnerShip", 'H2545', (0, 100))
        }

    def test_weapons(self):
        self.ois['TargetShip'].weapons['M1'].status


class TestWhoIsPlayerControlled(TestCase):
    """A ship answers from its own player, so a hull with nobody at the helm is an NPC."""

    def test_a_ship_with_a_player_is_player_controlled(self):
        ship = builder.create("Voyager", 'H2545', (0, 0), player='Rik')
        self.assertTrue(ship.is_player_controlled)

    def test_a_ship_with_no_player_is_not(self):
        ship = builder.create("Derelict", 'H2545', (0, 0))
        self.assertEqual('', ship.player)
        self.assertFalse(ship.is_player_controlled)

    def test_a_starbase_answers_the_same_way(self):
        base = builder.create("Sentinel", 'SB2531', (0, 0), player='Serge')
        self.assertTrue(base.is_player_controlled)
        self.assertFalse(builder.create("Hulk", 'SB2531', (0, 0)).is_player_controlled)

    def test_nothing_else_in_space_is(self):
        owner = builder.create("Shooter", 'H2545', (0, 0), player='Rik')
        rocket = Rocket().create('R', Vector(Point(0, 0), heading=0, speed=0), owner=owner)
        self.assertFalse(rocket.is_player_controlled)


class TestWhatLeavesAWreck(TestCase):
    """The graveyard keeps ships, whoever was flying them. Spent ordnance is not worth a record."""

    def test_a_ship_does_whether_or_not_it_has_a_player(self):
        self.assertTrue(builder.create("Voyager", 'H2545', (0, 0), player='Rik').leaves_a_wreck)
        self.assertTrue(builder.create("Derelict", 'H2545', (0, 0)).leaves_a_wreck)

    def test_a_starbase_does(self):
        self.assertTrue(builder.create("Sentinel", 'SB2531', (0, 0)).leaves_a_wreck)

    def test_a_missile_does_not(self):
        owner = builder.create("Shooter", 'H2545', (0, 0), player='Rik')
        rocket = Rocket().create('R', Vector(Point(0, 0), heading=0, speed=0), owner=owner)
        self.assertFalse(rocket.leaves_a_wreck)

    def test_a_mine_does_not(self):
        owner = builder.create("Layer", 'H2545', (0, 0), player='Rik')
        mine = SplinterMine().create('M', Vector(Point(0, 0), heading=0, speed=0), owner=owner)
        self.assertFalse(mine.leaves_a_wreck)
