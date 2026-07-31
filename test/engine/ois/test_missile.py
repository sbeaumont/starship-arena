from unittest import TestCase
from .ois_fixtures import create_ship_fixture, world_of
from arena.engine.objects.objectinspace import Vector, Point
from arena.engine.history import TICK_ZERO
from arena.engine.objects.registry import builder
from arena.engine.objects.registry.missiles import Splinter


class TestMissile(TestCase):
    def setUp(self) -> None:
        self.ois = create_ship_fixture()
        self.world = world_of(self.ois)
        self.missile = Splinter().create('TestSplinter', Vector(Point(0, 9), 0, 0), self.ois['OwnerShip'])

    def test_decide(self):
        tg = self.ois['TargetShip']
        self.missile.decide(self.world, TICK_ZERO)
        self.assertTrue(self.missile.is_destroyed)
        events = tg.history[TICK_ZERO].events
        self.assertEqual(len(events), 3)


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

    def _tick(self):
        """The order GameRound.do_tick uses: everything moves, then scans, then decides."""
        self.missile.move()
        self.missile.scan(self.world)
        self.missile.decide(self.world, TICK_ZERO)

    def test_it_turns_onto_a_target_it_has_scanned(self):
        self.assertEqual(0, self.missile.heading)

        self.missile.scan(self.world)
        self.missile.decide(self.world, TICK_ZERO)

        self.assertIs(self.target, self.missile.target)
        self.assertEqual(11.3, self.missile.heading, "bearing to the target from (0, 0)")

    def test_it_closes_on_a_target_it_would_otherwise_fly_past(self):
        """Straight ahead the closest it ever gets is 20, well outside a Splinter's 6."""
        for _ in range(4):
            if self.missile.is_destroyed:
                break
            self._tick()

        self.assertTrue(self.missile.is_destroyed, "should have reached its target and gone off")
        self.assertLessEqual(self.missile.distance_to(self.target.xy), self.missile.range)
