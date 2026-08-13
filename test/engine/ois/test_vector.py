from unittest import TestCase

from arena.engine.objects.geometry import Point, Vector


def vector(heading, speed):
    return Vector(Point(0, 0), heading=heading, speed=speed)


class TestDelta(TestCase):
    """Heading and speed, said the other way round."""

    def _delta(self, heading, speed):
        dx, dy = vector(heading, speed).delta
        return round(dx, 6), round(dy, 6)

    def test_north_is_positive_y(self):
        self.assertEqual((0.0, 60.0), self._delta(0, 60))

    def test_east_is_positive_x(self):
        self.assertEqual((60.0, 0.0), self._delta(90, 60))

    def test_south_and_west_are_the_negatives(self):
        self.assertEqual((0.0, -60.0), self._delta(180, 60))
        self.assertEqual((-60.0, 0.0), self._delta(270, 60))

    def test_reversing_travels_the_other_way(self):
        self.assertEqual((0.0, -20.0), self._delta(0, -20), "faces north, travels south")


class TestWithDelta(TestCase):
    """The way back, which is where a bounce lands."""

    def test_it_undoes_delta(self):
        original = vector(37, 45)
        round_tripped = original.with_delta(*original.delta)
        self.assertAlmostEqual(37, round_tripped.heading)
        self.assertAlmostEqual(45, round_tripped.speed)

    def test_it_keeps_the_position(self):
        moved = Vector(Point(12, 34), heading=0, speed=10).with_delta(60, 0)
        self.assertEqual(Point(12, 34), moved.pos)
        self.assertAlmostEqual(90, moved.heading)

    def test_reversing_stays_reversing(self):
        """It backed in, so it backs out: facing is kept and the speed stays negative."""
        astern = vector(0, -20)
        bounced = astern.with_delta(0, 6)
        self.assertAlmostEqual(180, bounced.heading, msg="travelling north, still facing astern")
        self.assertAlmostEqual(-6, bounced.speed)

    def test_a_reversing_round_trip_comes_back_unchanged(self):
        original = vector(0, -20)
        round_tripped = original.with_delta(*original.delta)
        self.assertAlmostEqual(0, round_tripped.heading)
        self.assertAlmostEqual(-20, round_tripped.speed)


class TestComponentAlong(TestCase):
    """How much of the travel runs a given way."""

    def test_all_of_it_when_they_agree(self):
        self.assertAlmostEqual(60, vector(90, 60).component_along(90))

    def test_none_of_it_when_square(self):
        self.assertAlmostEqual(0, vector(90, 60).component_along(0))

    def test_negative_when_it_runs_against(self):
        self.assertAlmostEqual(-60, vector(90, 60).component_along(270))

    def test_part_of_it_at_an_angle(self):
        self.assertAlmostEqual(60 * 0.5, vector(90, 60).component_along(30), places=6)