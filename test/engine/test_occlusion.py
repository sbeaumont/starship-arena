"""A body between two ships hides them from each other. See docs/gddr/0038."""
from unittest import TestCase

from arena.engine.gamedirectory import GameDirectory
from arena.engine.objects.registry import builder
from arena.engine.world import World

ROCK = 40


def world_with(*objects) -> World:
    return World(GameDirectory('/nowhere', 'none'), {o.name: o for o in objects})


def ship(name: str, x: float, y: float):
    return builder.create(name, 'H2545', (x, y))


def rock(x: float, y: float):
    return builder.create('Rock', 'Asteroid', (x, y))


class TestASightLine(TestCase):
    def setUp(self):
        self.alpha, self.beta = ship('Alpha', -100, 0), ship('Beta', 100, 0)

    def looking(self, *between) -> bool:
        return world_with(self.alpha, self.beta, *between).blocks_sight(self.alpha, self.beta)

    def test_nothing_in_the_way_is_not_blocked(self):
        self.assertFalse(self.looking(rock(0, 500)))

    def test_a_rock_on_the_line_blocks_it(self):
        self.assertTrue(self.looking(rock(0, 0)))

    def test_a_rock_grazed_by_the_line_blocks_it(self):
        self.assertTrue(self.looking(rock(0, ROCK - 1)))

    def test_a_rock_just_clear_of_the_line_does_not(self):
        self.assertFalse(self.looking(rock(0, ROCK + 1)))

    def test_a_rock_beyond_the_far_end_does_not_block(self):
        """The line stops at what is being looked at; what is behind it is not in the way."""
        self.assertFalse(self.looking(rock(200, 0)))

    def test_a_rock_behind_the_looker_does_not_block(self):
        self.assertFalse(self.looking(rock(-200, 0)))

    def test_neither_end_hides_itself(self):
        """A beacon carries a radius, so its own bulk sits at the end of every line to it."""
        beacon = builder.create('Gate', 'JumpPoint', (100, 0))
        world = world_with(self.alpha, beacon)
        self.assertFalse(world.blocks_sight(self.alpha, beacon))


class TestWhatAShipSees(TestCase):
    def test_it_scans_what_it_has_a_clear_line_to(self):
        alpha, beta = ship('Alpha', -60, 0), ship('Beta', 60, 0)
        world = world_with(alpha, beta)
        alpha.scan(world)

        self.assertEqual(['Beta'], [s.name for s in alpha.scans])

    def test_a_rock_between_them_hides_it(self):
        alpha, beta = ship('Alpha', -60, 0), ship('Beta', 60, 0)
        world = world_with(alpha, beta, rock(0, 0))
        alpha.scan(world)

        self.assertEqual([], list(alpha.scans))

    def test_terrain_is_never_scanned_because_it_is_on_the_chart(self):
        alpha = ship('Alpha', -60, 0)
        world = world_with(alpha, rock(0, 0))
        alpha.scan(world)

        self.assertEqual([], list(alpha.scans))

    def test_a_starbase_is_found_rather_than_charted(self):
        """It cannot move either, and being hard to hide is what visibility is for."""
        alpha = ship('Alpha', -60, 0)
        base = builder.create('Base', 'SB2531', (60, 0))
        world = world_with(alpha, base)
        alpha.scan(world)

        self.assertTrue(base.is_immovable)
        self.assertFalse(base.is_terrain)
        self.assertEqual(['Base'], [s.name for s in alpha.scans])