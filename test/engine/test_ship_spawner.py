"""A starbase brings a lost ship back: `Fire SS <wreck> <direction>`."""
import os
import shutil
import tempfile
from unittest import TestCase

from arena.app.services import AdminService
from arena.engine.admin import regenerate_game
from arena.engine.game import Game
from arena.engine.gamedirectory import GameDirectory
from arena.engine.history import Tick
from arena.engine.objects.components.spawner import ShipSpawner
from arena.engine.world import World

# Placed away from the origin, because setup scatters anything still sitting on it. Voyager is
# 20 off the base, so one 300 laser does 280: through a 100 shield and into 100 of hull.
ROSTER = [
    {'name': 'Base', 'type': 'SB2531', 'faction': 'One', 'player': 'Rik', 'x': 100, 'y': 0},
    {'name': 'Voyager', 'type': 'A2527', 'faction': 'One', 'player': 'Rik', 'x': 120, 'y': 0},
    {'name': 'Enemy', 'type': 'H2552', 'faction': 'Two', 'player': 'Piet', 'x': 600, 'y': 0},
]


class _Given:
    """A parameter that has already resolved, for firing a component directly."""

    def __init__(self, value):
        self.value = value
        self.object_name = getattr(value, 'name', value)


class TestNamingAReplacement(TestCase):
    """The stem is kept and the number climbs, so no name is ever handed out twice."""

    def _world(self, *names) -> World:
        return World(None, {n: None for n in names})

    def test_the_first_replacement_is_two(self):
        self.assertEqual('Voyager-2', ShipSpawner.replacement_name('Voyager', self._world('Voyager')))

    def test_it_climbs_past_the_ones_already_used(self):
        world = self._world('Voyager', 'Voyager-2', 'Voyager-3')
        self.assertEqual('Voyager-4', ShipSpawner.replacement_name('Voyager-2', world))

    def test_a_replacement_of_a_replacement_keeps_the_stem(self):
        world = self._world('Voyager', 'Voyager-2')
        self.assertEqual('Voyager-3', ShipSpawner.replacement_name('Voyager-2', world))


class TestFiringTheSpawner(TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        games = os.path.join(self.root, 'games')
        os.makedirs(games)
        admin = AdminService(games)
        admin.issue_login('Rik')
        admin.create_game('spawner', ROSTER)
        self.gd = GameDirectory(games, 'spawner')
        self.games = games
        # Round 1 kills Voyager, so round 2 has a wreck to claim.
        self._orders('Base', "1: Fire L1 Voyager\n")
        self._orders('Voyager', "")
        self._orders('Enemy', "")
        Game(self.gd).process_current_round()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _orders(self, ship: str, text: str, round_nr: int = 1):
        path = os.path.join(self.games, 'spawner', 'commands', f'{ship}-commands-{round_nr}.txt')
        with open(path, 'w') as f:
            f.write(text)

    def _run_round_two(self, base_orders: str):
        self._orders('Base', base_orders, 2)
        self._orders('Enemy', "", 2)
        Game(self.gd).process_current_round()
        return self.gd.load_current_world()

    def test_the_wreck_is_there_to_claim(self):
        self.assertIn('Voyager', self.gd.load_current_world().graveyard)

    def test_firing_it_puts_a_replacement_in_space(self):
        world = self._run_round_two("1: Fire SS Voyager 90\n")

        self.assertIn('Voyager-2', world.objects)
        replacement = world.objects['Voyager-2']
        self.assertEqual('Rik', replacement.player)
        self.assertEqual('One', replacement.faction)
        self.assertEqual('A2527', replacement.type_name, "same model as the wreck")
        self.assertEqual(0, replacement.score, "a new hull starts at nothing")

    def test_it_appears_off_the_base_facing_the_way_it_was_sent(self):
        world = self._run_round_two("1: Fire SS Voyager 90\n")

        replacement = world.objects['Voyager-2']
        self.assertEqual(90, replacement.heading)
        self.assertEqual(ShipSpawner.launch_distance,
                         world.objects['Base'].distance_to(replacement.xy))

    def test_the_base_counts_down_what_is_left(self):
        world = self._run_round_two("1: Fire SS Voyager 90\n")

        self.assertEqual({'Replacements': 2}, world.objects['Base'].weapons['SS'].status)

    def test_a_name_that_is_not_a_wreck_is_refused(self):
        world = self._run_round_two("1: Fire SS Enemy 90\n")

        self.assertNotIn('Enemy-2', world.objects)

    def test_a_replacement_takes_orders_the_round_after(self):
        self._run_round_two("1: Fire SS Voyager 90\n")

        self.assertIn('Voyager-2', Game(self.gd).missing_command_files)

    def test_the_fourth_replacement_is_refused(self):
        """Three a game is what stops a game running forever."""
        base = self.gd.load_current_world().objects['Base']
        spawner = base.weapons['SS']
        wreck = self.gd.load_current_world().graveyard['Voyager']
        params = {'wreck': _Given(wreck), 'direction': _Given(90)}
        world = self.gd.load_current_world()

        made = [spawner.fire(params, world, Tick(2, 1)) for _ in range(4)]

        self.assertEqual(3, len([s for s in made if s]))
        self.assertIsNone(made[3])
        self.assertEqual(0, spawner.ammo)

    def test_replenishing_does_not_refill_it(self):
        """A replenish resets every weapon, so spending three has to be for the whole game."""
        world = self._run_round_two("1: Fire SS Voyager 90\n")
        base = world.objects['Base']

        base.replenish(base)

        self.assertEqual(2, base.weapons['SS'].ammo)
        self.assertEqual(base._type.weapons[2].ammo, base.weapons['S1'].ammo, "a launcher does refill")

    def test_it_comes_back_once_on_a_regenerate(self):
        """The Fire order is the record of the spawn, which is why it is in no plan file."""
        self._run_round_two("1: Fire SS Voyager 90\n")

        regenerate_game(self.gd)

        world = self.gd.load_current_world()
        self.assertIn('Voyager-2', world.objects)
        self.assertNotIn('Voyager-3', world.objects, "replayed once, not twice")
        self.assertEqual(2, world.objects['Base'].weapons['SS'].ammo)