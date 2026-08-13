from unittest import TestCase

from arena.engine.history import TICK_ZERO, Tick
from arena.engine.objects.geometry import Point, Vector
from arena.engine.objects.registry import builder
from arena.engine.objects.registry.missiles import Splinter

from .ois_fixtures import create_ship_fixture, run_ticks, world_of


class TestMissile(TestCase):
    def setUp(self) -> None:
        self.ois = create_ship_fixture()
        self.missile = Splinter().create('TestSplinter', Vector(Point(0, 9), 0, 0),
                                         self.ois['OwnerShip'])
        self.ois['TestSplinter'] = self.missile
        self.world = world_of(self.ois)

    def test_it_goes_off_on_what_it_reaches(self):
        """Launched a unit off TargetShip at (0, 10), inside a SplinterWarhead's 6."""
        run_ticks(self.world)

        self.assertTrue(self.missile.is_destroyed)
        target = self.ois['TargetShip']
        self.assertTrue(any(e.kind == 'explosion' for e in target.history[Tick(1, 1)].events))


class TestGuidedMissileIntercepts(TestCase):
    """A Splinter turns onto what it scans, which is the whole difference from a Rocket."""

    def setUp(self):
        self.shooter = builder.create("Shooter", "H2545", (0, 0))
        self.shooter.faction = 'One'
        self.target = builder.create("Target", "H2545", (20, 100))
        self.target.faction = 'Two'
        self.missile = Splinter().create('S', Vector(Point(0, 0), heading=0, speed=0),
                                         owner=self.shooter)
        self.ois = {'Shooter': self.shooter, 'Target': self.target, 'S': self.missile}
        self.world = world_of(self.ois)

    def test_it_turns_onto_a_target_it_has_scanned(self):
        self.assertEqual(0, self.missile.heading)

        self.missile.scan(self.world)
        self.missile.decide(self.world, TICK_ZERO)

        self.assertIs(self.target, self.missile.target)
        self.assertEqual(11.3, self.missile.heading, "bearing to the target from (0, 0)")

    def test_it_closes_on_a_target_it_would_otherwise_fly_past(self):
        """Straight ahead the closest it ever gets is 20, well outside a Splinter's 6."""
        run_ticks(self.world, 4)

        self.assertTrue(self.missile.is_destroyed, "should have reached its target and gone off")
        self.assertLessEqual(self.missile.distance_to(self.target.xy), self.missile.range)
