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
from arena.engine.objects.components.spawner import CLAIMED, ShipSpawner
from arena.engine.objects.registry import builder
from arena.engine.world import World

# Placed away from the origin, because a scenario deploys anything still sitting on it. Voyager is
# 20 off the base, where a 300 laser reaching 60 does 133. The first shot breaks a 100 shield and
# takes 33 hull, the second lands whole on 100 of hull, so it takes both of the base's lasers.
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
        return World(None, {n: builder.create(n, 'A2527', (0, 0)) for n in names})

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
        admin = AdminService(self.root)
        admin.issue_login('Rik')
        admin.create_game('spawner', ROSTER, 'generic')
        self.gd = GameDirectory(games, 'spawner')
        self.games = games
        # Round 1 kills Voyager, so round 2 has a wreck to claim.
        self._orders('Base', "1: Fire L1 Voyager\n1: Fire L2 Voyager\n")
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
        self.assertEqual((world.objects['Base'].heading + 90) % 360, replacement.heading,
                         "the direction is the base's own, and the base faces the middle")
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

    def test_a_wreck_can_only_be_claimed_once(self):
        world = self._run_round_two("1: Fire SS Voyager 90\n2: Fire SS Voyager 180\n")

        self.assertIn(CLAIMED, world.graveyard['Voyager'].tags)
        self.assertIn('Voyager-2', world.objects)
        self.assertNotIn('Voyager-3', world.objects)
        self.assertEqual(2, world.objects['Base'].weapons['SS'].ammo, "the refusal costs nothing")

    def test_the_refusal_is_told_to_the_player(self):
        world = self._run_round_two("1: Fire SS Voyager 90\n2: Fire SS Voyager 180\n")

        said = [str(e) for th in world.objects['Base'].history.ticks.values() for e in th.events]
        self.assertTrue(any('already been replaced' in s for s in said), said)

    def test_another_faction_s_wreck_is_refused(self):
        world = self.gd.load_current_world()
        theirs = builder.create('TheirLoss', 'A2527', (0, 0), player='Piet')
        theirs.faction = 'Two'
        world.add_to_graveyard(theirs)
        spawner = world.objects['Base'].weapons['SS']

        made = spawner.fire({'wreck': _Given(theirs), 'direction': _Given(90)}, world, Tick(2, 1))

        self.assertIsNone(made)
        self.assertEqual(3, spawner.ammo, "a refusal costs nothing")

    def test_only_our_own_unclaimed_wrecks_are_offered(self):
        world = self._run_round_two("1: Fire SS Voyager 90\n")
        theirs = builder.create('TheirLoss', 'A2527', (0, 0), player='Piet')
        theirs.faction = 'Two'
        world.add_to_graveyard(theirs)
        wreck_input = world.objects['Base'].weapons['SS'].expected_parameters[0]
        wreck_input.set_world(world)

        self.assertEqual([], wreck_input.choices, "Voyager is claimed, TheirLoss is not ours")

    def test_the_claim_survives_a_regenerate(self):
        self._run_round_two("1: Fire SS Voyager 90\n")

        regenerate_game(self.gd)

        self.assertIn(CLAIMED, self.gd.load_current_world().graveyard['Voyager'].tags)

    def test_the_fourth_replacement_is_refused(self):
        """Three a game is what stops a game running forever. Four wrecks, so the claim rule
        is not what does the refusing."""
        world = self.gd.load_current_world()
        spawner = world.objects['Base'].weapons['SS']
        wrecks = [builder.create(f"Lost{n}", 'A2527', (0, 0), player='Rik') for n in range(4)]
        for wreck in wrecks:
            wreck.faction = 'One'
            world.add_to_graveyard(wreck)

        made = [spawner.fire({'wreck': _Given(w), 'direction': _Given(90)}, world, Tick(2, 1))
                for w in wrecks]

        self.assertEqual(3, len([s for s in made if s]))
        self.assertIsNone(made[3])
        self.assertEqual(0, spawner.ammo)

    def test_replenishing_does_not_refill_it(self):
        """A replenish resets every weapon, so spending three has to be for the whole game."""
        world = self._run_round_two("1: Fire SS Voyager 90\n")
        base = world.objects['Base']

        base.replenish()

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