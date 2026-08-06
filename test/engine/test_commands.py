from unittest import TestCase

from arena.engine.command import Command, CommandLine
from arena.engine.history import TICK_ZERO
from arena.engine.objects.registry import builder
from test.engine.ois.ois_fixtures import world_of


def _command(text: str, ship, world):
    return Command.for_command_line(CommandLine(text), ship, world)


class TestComponentCommandsReachTheirComponent(TestCase):
    """A component command has to arrive at the component it names.

    An activation order went through the ship by name for a while and the name never arrived, so
    every order validated, executed and did nothing. Nothing caught it, because a component that
    refuses only records an event."""

    def setUp(self):
        self.ship = builder.create("Cloaky", 'H2552', (0, 0))
        self.world = world_of({'Cloaky': self.ship})
        self.cloak = self.ship.ecm['C1']

    def test_a_cloak_takes_the_power_it_is_given(self):
        command = _command("1: Power C1 4", self.ship, self.world)
        self.assertTrue(command.is_valid, command.feedback_results)
        command.execute(TICK_ZERO)
        self.assertEqual(4, self.cloak.power)

    def test_powering_up_pays_for_the_tick_it_happens_in(self):
        before = self.ship.battery
        _command("1: Power C1 4", self.ship, self.world).execute(TICK_ZERO)
        self.assertEqual(before - 4, self.ship.battery)

    def test_raising_the_power_pays_only_the_increase(self):
        _command("1: Power C1 2", self.ship, self.world).execute(TICK_ZERO)
        before = self.ship.battery
        _command("2: Power C1 6", self.ship, self.world).execute(TICK_ZERO)
        self.assertEqual(before - 4, self.ship.battery)

    def test_dropping_the_power_costs_nothing(self):
        _command("1: Power C1 6", self.ship, self.world).execute(TICK_ZERO)
        before = self.ship.battery
        _command("2: Power C1 0", self.ship, self.world).execute(TICK_ZERO)
        self.assertEqual(0, self.cloak.power)
        self.assertEqual(before, self.ship.battery)

    def test_beyond_twice_the_generators_is_refused(self):
        ceiling = 2 * self.ship.generators
        self.assertTrue(_command(f"1: Power C1 {ceiling}", self.ship, self.world).is_valid)
        self.assertFalse(_command(f"1: Power C1 {ceiling + 1}", self.ship, self.world).is_valid)

    def test_an_unknown_component_is_refused(self):
        self.assertFalse(_command("1: Power NOPE 4", self.ship, self.world).is_valid)

    def test_a_component_that_takes_no_power_is_refused(self):
        """A laser wants a target name, so a number is not something it can be handed."""
        self.assertFalse(_command("1: Power L1 4", self.ship, self.world).is_valid)


class TestBoost(TestCase):
    """Boost names its component like every other component order, so one grammar covers all."""

    def setUp(self):
        self.ship = builder.create("Booster", 'H2552', (0, 0))
        self.world = world_of({'Booster': self.ship})
        self.shields = self.ship.defense[0]

    def test_it_moves_energy_into_the_quadrant(self):
        before = self.ship.battery
        command = _command("1: Boost Shields N 40", self.ship, self.world)
        self.assertTrue(command.is_valid, command.feedback_results)
        command.execute(TICK_ZERO)
        self.assertEqual(before - 40, self.ship.battery)
        self.assertEqual(self.shields.max_strengths['N'] + 40, self.shields.strengths['N'])

    def test_twice_the_quadrant_is_the_ceiling(self):
        ceiling = 2 * self.shields.max_strengths['N']
        self.assertFalse(_command(f"1: Boost Shields N {ceiling + 1}", self.ship, self.world).is_valid)

    def test_a_quadrant_that_is_not_a_quadrant_is_refused(self):
        self.assertFalse(_command("1: Boost Shields Q 40", self.ship, self.world).is_valid)

    def test_it_wants_both_words(self):
        self.assertFalse(_command("1: Boost Shields N", self.ship, self.world).is_valid)

    def test_a_component_that_does_not_boost_is_refused(self):
        self.assertFalse(_command("1: Boost L1 N 40", self.ship, self.world).is_valid)


class TestLaserFalloff(TestCase):
    """The short-range weapon: full damage at nothing, squared away to nothing at its reach."""

    def _damage_at(self, distance):
        shooter = builder.create("Shooter", 'H2545', (0, 0))
        target = builder.create("Target", 'H2545', (0, distance))
        shooter.weapons['L1'].damage = 200
        shooter.weapons['L1'].reach = 100
        return shooter.weapons['L1'].damage_to(target)

    def test_point_blank_is_the_whole_damage(self):
        self.assertEqual(200, self._damage_at(0))

    def test_half_reach_leaves_a_quarter(self):
        self.assertEqual(50, self._damage_at(50))

    def test_it_falls_faster_than_linear(self):
        """A tenth of the way out costs a fifth, which is what makes closing worth the risk."""
        self.assertEqual(162, self._damage_at(10))

    def test_at_its_reach_it_does_nothing(self):
        self.assertEqual(0, self._damage_at(100))

    def test_past_its_reach_it_stays_nothing(self):
        """The square climbs again beyond reach, so out of range has to be answered first."""
        self.assertEqual(0, self._damage_at(150))
        self.assertEqual(0, self._damage_at(300))


class TestCloakHiding(TestCase):
    """Power halves an enemy's scan range every `half_power`, so it is bought, not switched on."""

    def setUp(self):
        self.ship = builder.create("Cloaky", 'H2552', (0, 0))
        self.cloak = self.ship.ecm['C1']

    def test_unpowered_it_hides_nothing(self):
        self.assertEqual(200, self.ship.modify_scan_range(200))

    def test_its_half_power_halves(self):
        self.cloak.power = self.cloak.half_power
        self.assertEqual(100, self.ship.modify_scan_range(200))

    def test_twice_that_quarters(self):
        self.cloak.power = 2 * self.cloak.half_power
        self.assertEqual(50, self.ship.modify_scan_range(200))

    def test_it_shuts_down_when_the_battery_cannot_pay(self):
        self.cloak.power = 8
        self.ship.battery = 3
        self.ship.use_energy()
        self.assertEqual(0, self.cloak.power)
        self.assertEqual(3, self.ship.battery)

    def test_it_draws_every_tick_while_it_holds(self):
        self.cloak.power = 5
        before = self.ship.battery
        self.ship.use_energy()
        self.ship.use_energy()
        self.assertEqual(before - 10, self.ship.battery)