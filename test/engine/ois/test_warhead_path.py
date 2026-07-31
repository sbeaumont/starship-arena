from unittest import TestCase

from arena.engine.history import TICK_ZERO
from arena.engine.objects.objectinspace import Point, Vector
from arena.engine.objects.registry import builder
from arena.engine.objects.registry.missiles import Rocket

from .ois_fixtures import world_of


class TestWarheadTriggersOnItsPath(TestCase):
    """A tick is a jump, so a warhead has to test the path it flew, not where the tick ended.

    A Rocket covers 60 a tick and triggers within 20, so a target sitting between two tick
    boundaries used to be passed straight through.
    """

    def setUp(self):
        self.shooter = builder.create("Shooter", "H2545", (0, 0))
        self.shooter.faction = 'One'
        self.target = builder.create("Target", "H2545", (90, 0))
        self.target.faction = 'Two'
        self.ois = {'Shooter': self.shooter, 'Target': self.target}
        self.world = world_of(self.ois)

    def _rocket_heading_east(self):
        rocket = Rocket().create("R", Vector(Point(0, 0), heading=90, speed=0), owner=self.shooter)
        self.ois['R'] = rocket
        return rocket

    def _tick(self, rocket):
        rocket.move()
        rocket.decide(self.world, TICK_ZERO)

    def test_rocket_explodes_where_it_first_came_into_range(self):
        rocket = self._rocket_heading_east()

        self._tick(rocket)
        self.assertEqual(Point(60.0, 0.0), rocket.pos)
        self.assertFalse(rocket.is_destroyed, "target is still 30 away, out of the warhead's 20")

        # Second tick ends at 120, so both ends of the leg are 30 from the target at 90.
        self._tick(rocket)
        self.assertTrue(rocket.is_destroyed)
        self.assertEqual(Point(70.0, 0.0), rocket.pos)

    def test_a_target_that_is_never_in_range_is_missed(self):
        self.target.place_at(Point(90, 40))
        rocket = self._rocket_heading_east()

        self._tick(rocket)
        self._tick(rocket)

        self.assertFalse(rocket.is_destroyed)
        self.assertEqual(Point(120.0, 0.0), rocket.pos)

    def test_the_gap_is_measured_against_a_target_that_moves_too(self):
        """Closing head on, both legs count: the target covers half the gap itself."""
        self.target.place_at(Point(200, 0))
        self.target.vector = Vector(Point(200, 0), heading=270, speed=60)
        rocket = self._rocket_heading_east()

        rocket.move()
        self.target.move()
        rocket.decide(self.world, TICK_ZERO)

        # Rocket 0 -> 60, target 200 -> 140: the gap closes from 200 to 80, never within 20.
        self.assertFalse(rocket.is_destroyed)

        rocket.move()
        self.target.move()
        rocket.decide(self.world, TICK_ZERO)

        # Both cover 60, so the 80 gap closes at 120 a tick and reaches 20 half way along.
        self.assertTrue(rocket.is_destroyed)
        self.assertEqual(Point(90.0, 0.0), rocket.pos)
        self.assertEqual(20.0, rocket.distance_to(self.target.position_at(0.5)))


class TestApproachFraction(TestCase):
    """The geometry on its own."""

    def setUp(self):
        self.mover = builder.create("Mover", "H2545", (0, 0))
        self.other = builder.create("Other", "H2545", (0, 0))

    def _leg(self, ois, start: tuple, end: tuple):
        ois.place_at(Point(*start))
        ois.vector = Vector(Point(*end), heading=0, speed=0)

    def test_already_within_range_at_the_start(self):
        self._leg(self.mover, (0, 0), (60, 0))
        self._leg(self.other, (10, 0), (10, 0))
        self.assertEqual(0.0, self.mover.approach_fraction(self.other, 20))

    def test_entering_range_part_way_through(self):
        self._leg(self.mover, (0, 0), (100, 0))
        self._leg(self.other, (50, 0), (50, 0))
        self.assertAlmostEqual(0.3, self.mover.approach_fraction(self.other, 20))
        self.assertEqual(Point(30.0, 0.0), self.mover.position_at(0.3).rounded(1))

    def test_passing_by_too_wide(self):
        self._leg(self.mover, (0, 0), (100, 0))
        self._leg(self.other, (50, 40), (50, 40))
        self.assertIsNone(self.mover.approach_fraction(self.other, 20))

    def test_running_parallel_never_closes(self):
        self._leg(self.mover, (0, 0), (60, 0))
        self._leg(self.other, (0, 30), (60, 30))
        self.assertIsNone(self.mover.approach_fraction(self.other, 20))