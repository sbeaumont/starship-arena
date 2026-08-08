"""A ship the director schedules arrives mid-round, and survives a regenerate."""
import os
import shutil
import tempfile
from unittest import TestCase

from arena.app.services import AdminService
from arena.engine.admin import regenerate_game
from arena.engine.game import Game
from arena.engine.gamedirectory import GameDirectory
from arena.engine.history import Tick

ROSTER = [
    {'name': 'Voyager', 'type': 'H2545', 'faction': 'One', 'player': 'Rik', 'x': 0, 'y': 0},
    {'name': 'Shaper', 'type': 'H2552', 'faction': 'Two', 'player': 'Piet', 'x': 400, 'y': 0},
]


class TestASpawnedShip(TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.games = os.path.join(self.root, 'games')
        self.admin = AdminService(self.root)
        self.admin.issue_login('Rik')
        self.admin.create_game('spawning', ROSTER)
        self.gd = GameDirectory(self.games, 'spawning')
        for ship in ('Voyager', 'Shaper'):
            self._orders(ship, "1: A10\n")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _orders(self, ship: str, text: str, round_nr: int = 1):
        path = os.path.join(self.games, 'spawning', 'commands', f'{ship}-commands-{round_nr}.txt')
        with open(path, 'w') as f:
            f.write(text)

    def _schedule(self, name='Newcomer', tick=3, **kwargs):
        self.admin.spawn_ship('spawning', name, 'A2527', player='Rik', faction='One',
                              x=100, y=50, heading=90, tick=tick, **kwargs)

    def test_it_is_written_to_the_plan_not_the_world(self):
        self._schedule()

        self.assertEqual([{'round': 1, 'tick': 3, 'name': 'Newcomer', 'type': 'A2527',
                           'x': 100, 'y': 50, 'heading': 90,
                           'player': 'Rik', 'faction': 'One'}],
                         self.gd.load_spawns())
        self.assertNotIn('Newcomer', self.gd.load_current_world().objects)

    def test_it_arrives_at_its_tick_and_not_before(self):
        self._schedule(tick=3)

        Game(self.gd).process_current_round()

        world = self.gd.load_current_world()
        newcomer = world.objects['Newcomer']
        self.assertEqual(Tick(1, 3), newcomer.history.first)
        self.assertNotIn(Tick(1, 2), newcomer.history)
        self.assertEqual('Rik', newcomer.player)
        self.assertEqual('One', newcomer.faction)

    def test_it_is_placed_and_pointed_where_the_plan_says(self):
        self._schedule(tick=1)

        Game(self.gd).process_current_round()

        arrival = self.gd.load_world(1).objects['Newcomer'].history[Tick(1, 1)]
        self.assertEqual(100, arrival['pos'].x)
        self.assertEqual(50, arrival['pos'].y)
        self.assertEqual(90, arrival['heading'])

    def test_a_name_the_game_has_used_is_refused(self):
        with self.assertRaises(ValueError):
            self.admin.spawn_ship('spawning', 'Voyager', 'A2527')

    def test_an_unknown_type_is_refused(self):
        with self.assertRaises(ValueError):
            self.admin.spawn_ship('spawning', 'Newcomer', 'NoSuchType')

    def test_it_can_be_scheduled_for_a_later_round(self):
        self.admin.spawn_ship('spawning', 'Later', 'A2527', round_nr=4)

        self.assertEqual(4, self.gd.load_spawns()[0]['round'])
        Game(self.gd).process_current_round()
        self.assertNotIn('Later', self.gd.load_current_world().objects)

    def test_a_round_already_played_is_refused(self):
        Game(self.gd).process_current_round()

        with self.assertRaises(ValueError):
            self.admin.spawn_ship('spawning', 'TooLate', 'A2527', round_nr=1)

    def test_it_takes_orders_the_round_after_it_arrives(self):
        self._schedule(tick=3)
        Game(self.gd).process_current_round()

        self.assertIn('Newcomer', Game(self.gd).missing_command_files)

    def test_it_comes_back_the_same_on_a_regenerate(self):
        self._schedule(tick=3)
        Game(self.gd).process_current_round()
        before = self.gd.load_current_world().objects['Newcomer'].pos

        regenerate_game(self.gd)

        after = self.gd.load_current_world().objects['Newcomer']
        self.assertEqual(before, after.pos)
        self.assertEqual(Tick(1, 3), after.history.first)