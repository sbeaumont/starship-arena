from unittest import TestCase

from arena.engine.history import Tick, TICK_ZERO
from arena.engine.objects.component import DirectionParameter
from arena.engine.objects.components.launcher import Launcher
from arena.engine.objects.registry import builder
from arena.engine.objects.registry.mines import SplinterMine
from arena.engine.objects.registry.missiles import Rocket


class TestLaunchedThingsStartAtTheTickTheyWereLaunched(TestCase):
    """A launcher hands its payload the tick, so the payload's history starts there.

    Everything ever launched used to start at TICK_ZERO, which is round 1's opening state.
    A missile fired in round 1 therefore rendered as though it had been sitting there before
    the round began, and had no entry at all for the tick it was actually fired.
    """

    def setUp(self):
        self.shooter = builder.create("Shooter", "H2545", (0, 0))
        self.shooter.faction = 'One'
        self.ois = {'Shooter': self.shooter}
        self.tick = Tick(3, 4)

    def _launcher(self, payload_type, name='L1'):
        launcher = Launcher(name, payload_type, 5)
        launcher.attach(self.shooter)
        return launcher

    def _direction(self, launcher, angle: str):
        p = DirectionParameter('direction', launcher)
        p.input(angle)
        return {'direction': p}

    def test_a_missile_starts_its_history_at_the_launch_tick(self):
        launcher = self._launcher(Rocket())

        missile = launcher.fire(self._direction(launcher, '90'), self.ois, self.tick)

        self.assertIn(self.tick, missile.history)
        self.assertNotIn(TICK_ZERO, missile.history)

    def test_a_mine_does_too(self):
        launcher = self._launcher(SplinterMine(), name='M1')

        mine = launcher.fire(self._direction(launcher, '0'), self.ois, self.tick)

        self.assertIn(self.tick, mine.history)
        self.assertNotIn(TICK_ZERO, mine.history)

    def test_the_launch_tick_records_where_it_was_launched(self):
        """The snapshot for that tick has to be the payload's own, not an empty placeholder."""
        launcher = self._launcher(Rocket())

        missile = launcher.fire(self._direction(launcher, '90'), self.ois, self.tick)
        missile.history.update()

        snapshot = missile.history[self.tick]
        self.assertEqual(missile.name, snapshot['name'])
        # Placed clear of its own blast: a RocketWarhead reaches 20, so 21 east of the ship.
        self.assertEqual(21.0, snapshot['pos'].x)