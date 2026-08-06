from unittest import TestCase

from arena.engine.history import Tick
from arena.engine.objects.objectinspace import Leg, Point, Vector
from arena.engine.objects.registry import builder
from arena.engine.objects.registry.missiles import Rocket
from arena.engine.round import GameRound

from .ois_fixtures import world_of


class TestWarheadTriggersOnItsPath(TestCase):
    """A tick is a jump, so a warhead has to test the leg, not where the tick ended.

    A Rocket covers 60 a tick and triggers within 20, so a target sitting between two tick
    boundaries would be passed straight through. It stops where the two legs came closest, so the
    target is at the middle of the blast rather than on its rim.
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

    def _ticks(self, how_many):
        game_round = GameRound(self.world, 1)
        for tick in Tick.for_start_of_round(1).ticks_for_round[:how_many]:
            game_round.do_tick(tick)

    def test_rocket_explodes_where_it_passed_closest(self):
        rocket = self._rocket_heading_east()

        self._ticks(1)
        self.assertEqual(Point(60.0, 0.0), rocket.pos)
        self.assertFalse(rocket.is_destroyed, "target is still 30 away, out of the warhead's 20")

        # Second tick would end at 120, so both ends of the leg are 30 from the target at 90.
        self._ticks(1)
        self.assertTrue(rocket.is_destroyed)
        self.assertEqual(Point(89.9, 0.0), rocket.pos)
        self.assertEqual(0.1, rocket.distance_to(self.target.xy), "a hair short, so the hit has a bearing")

    def test_a_target_that_is_never_in_range_is_missed(self):
        self.target.place_at(Point(90, 40))
        rocket = self._rocket_heading_east()

        self._ticks(2)

        self.assertFalse(rocket.is_destroyed)
        self.assertEqual(Point(120.0, 0.0), rocket.pos)

    def test_the_gap_is_measured_against_a_target_that_moves_too(self):
        """Closing head on, both legs count: the target covers half the gap itself."""
        self.target.place_at(Point(200, 0))
        self.target.vector = Vector(Point(200, 0), heading=270, speed=60)
        rocket = self._rocket_heading_east()

        # Rocket 0 -> 60, target 200 -> 140: the gap closes from 200 to 80, never within 20.
        self._ticks(1)
        self.assertFalse(rocket.is_destroyed)

        # Both cover 60, so the 80 gap closes at 120 a tick and runs out two thirds along.
        self._ticks(1)
        self.assertTrue(rocket.is_destroyed)


class TwoLegs(TestCase):
    """Legs on their own: a start and a change in x and y, with no object attached."""

    @staticmethod
    def _leg(start: tuple, end: tuple) -> Leg:
        return Leg(Point(*start), (end[0] - start[0], end[1] - start[1]))


class TestClosestFraction(TwoLegs):
    """Where along the leg the gap was shortest."""

    def test_the_shortest_gap_is_square_to_the_leg(self):
        mover = self._leg((0, 0), (100, 0))
        self.assertAlmostEqual(0.5, mover.closest_fraction(self._leg((50, 10), (50, 10)), 20))

    def test_within_range_at_the_start_but_closer_further_on(self):
        """It is beside the other at 1/6, and stops a hair short so the gap has a direction."""
        mover = self._leg((0, 0), (60, 0))
        fraction = mover.closest_fraction(self._leg((10, 0), (10, 0)), 20)
        self.assertAlmostEqual(9.9 / 60, fraction, places=6)

    def test_still_closing_when_the_leg_ends(self):
        """Nothing past the end of the leg is there to be closest to, so the end of it is."""
        mover = self._leg((0, 0), (100, 0))
        self.assertEqual(1.0, mover.closest_fraction(self._leg((115, 0), (115, 0)), 20))

    def test_receding_from_the_first_moment(self):
        mover = self._leg((0, 0), (100, 0))
        self.assertEqual(0.0, mover.closest_fraction(self._leg((-15, 0), (-15, 0)), 20))

    def test_a_direct_hit_stops_short_enough_to_have_a_bearing(self):
        """Dead on the other there is no direction, and a shield would not know which way to face."""
        mover = self._leg((0, 0), (100, 0))
        self.assertAlmostEqual(49.9 / 100, mover.closest_fraction(self._leg((50, 0), (50, 0)), 20),
                               places=6)

    def test_passing_by_too_wide(self):
        mover = self._leg((0, 0), (100, 0))
        self.assertIsNone(mover.closest_fraction(self._leg((50, 40), (50, 40)), 20))

    def test_running_parallel_never_closes(self):
        mover = self._leg((0, 0), (60, 0))
        self.assertIsNone(mover.closest_fraction(self._leg((0, 30), (60, 30)), 20))


class TestApproachFraction(TwoLegs):
    """Where along the leg the gap first closed to a given distance."""

    def test_already_within_range_at_the_start(self):
        mover = self._leg((0, 0), (60, 0))
        self.assertEqual(0.0, mover.approach_fraction(self._leg((10, 0), (10, 0)), 20))

    def test_entering_range_part_way_through(self):
        mover = self._leg((0, 0), (100, 0))
        self.assertAlmostEqual(0.3, mover.approach_fraction(self._leg((50, 0), (50, 0)), 20))

    def test_passing_by_too_wide(self):
        mover = self._leg((0, 0), (100, 0))
        self.assertIsNone(mover.approach_fraction(self._leg((50, 40), (50, 40)), 20))

    def test_running_parallel_never_closes(self):
        mover = self._leg((0, 0), (60, 0))
        self.assertIsNone(mover.approach_fraction(self._leg((0, 30), (60, 30)), 20))
