from unittest import TestCase

from arena.engine.history import Tick, TICK_ZERO
from arena.engine.objects.event import ExplosionEvent
from arena.engine.objects.geometry import Point, Vector
from arena.engine.objects.registry import builder
from arena.engine.objects.registry.missiles import Rocket

from .ois_fixtures import run_ticks, world_of


def went_off(world, name) -> bool:
    return any(isinstance(e, ExplosionEvent) and e.source.name == name
               for o in world.objects.values() for t in o.history.ticks
               for e in o.history[t].events)


class TestAWarheadGoesOffWhenItsContainerDies(TestCase):
    """Whatever kills a missile sets it off, so one blast carries to the next."""

    def setUp(self):
        self.shooter = builder.create("Shooter", "H2545", (0, 0), player='Rik')
        self.shooter.faction = 'One'
        self.foe = builder.create("Foe", "H2545", (100, 0))
        self.foe.faction = 'Two'

    def _parked(self, name, x):
        rocket = Rocket().create(name, Vector(Point(x, 0), heading=90, speed=0),
                                 owner=self.shooter)
        rocket.vector.speed = 0
        return rocket

    def test_a_blast_carries_to_the_missile_it_kills(self):
        # A is 15 from the Foe so it triggers. B is 20 from A, inside its blast, and 35 from the
        # Foe, so nothing of its own would ever set it off.
        first, second = self._parked('A', 85), self._parked('B', 65)
        world = world_of({'Shooter': self.shooter, 'Foe': self.foe, 'A': first, 'B': second})

        run_ticks(world)

        self.assertTrue(went_off(world, 'A'))
        self.assertTrue(went_off(world, 'B'), "killed by A's blast, so it goes off too")

    def test_running_out_of_battery_is_still_a_fizzle(self):
        """The tick drains the battery after deciding, so a spent missile never gets to go off."""
        lone = Rocket().create('Lone', Vector(Point(0, 500), heading=90, speed=60),
                               owner=self.shooter)
        world = world_of({'Shooter': self.shooter, 'Lone': lone})

        run_ticks(world, 10)
        run_ticks(world, 10, round_nr=2)

        self.assertTrue(lone.is_destroyed)
        self.assertEqual(0, lone.battery)
        self.assertFalse(went_off(world, 'Lone'))