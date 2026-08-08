"""Terrain comes from bodies.jsonl and is in the world from tick zero."""
import json
import os
import shutil
import tempfile
from unittest import TestCase

from arena.app.services import AdminService, GameService
from arena.engine.game import Game
from arena.app.scenarios.five_faction_war import FiveFactionWar, RING_BODIES, RING_RADIUS
from arena.engine.admin import regenerate_game, setup_game
from arena.engine.gamedirectory import GameDirectory
from arena.engine.objects.objectinspace import Point

ROSTER = [
    {'name': 'Alpha', 'type': 'H2545', 'faction': 'One', 'player': 'Rik', 'x': 400, 'y': 0},
    {'name': 'Beta', 'type': 'F2551', 'faction': 'Two', 'player': 'Piet', 'x': -400, 'y': 0},
]
BODIES = [{'name': 'Rock', 'type': 'Asteroid', 'x': 0, 'y': 0}]


class TestSetupReadsTerrain(TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, 'terrain'))
        self.gd = GameDirectory(self.root, 'terrain')
        self._write('ships.jsonl', ROSTER)
        self._write('bodies.jsonl', BODIES)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write(self, name, records):
        with open(os.path.join(self.root, 'terrain', name), 'w') as f:
            f.write('\n'.join(json.dumps(r) for r in records) + '\n')

    def test_a_body_is_in_the_world_from_the_start(self):
        setup_game(self.gd)
        world = self.gd.load_current_world()

        self.assertIn('Rock', world.objects)
        self.assertEqual(40, world.objects['Rock'].radius)

    def test_it_sits_exactly_where_it_was_written(self):
        """Ships on the origin get scattered. Terrain never does."""
        setup_game(self.gd)

        self.assertEqual(Point(0.0, 0.0), self.gd.load_current_world().objects['Rock'].pos)

    def test_it_survives_a_regenerate(self):
        setup_game(self.gd)
        regenerate_game(self.gd)

        self.assertIn('Rock', self.gd.load_current_world().objects)

    def test_a_game_without_a_bodies_file_is_empty_space(self):
        os.remove(os.path.join(self.root, 'terrain', 'bodies.jsonl'))
        setup_game(self.gd)

        world = self.gd.load_current_world()
        self.assertEqual([], [o for o in world.objects.values() if o.radius])


class TestTerrainReachesThePlayer(TestCase):
    """A scanned rock is a contact like any other, and says it is on nobody's side."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.games = os.path.join(self.root, 'games')
        os.makedirs(os.path.join(self.games, 'terr', 'commands'))
        # Off the origin, or setup scatters them and nothing ends up near the rock.
        ships = [{'name': 'Alpha', 'type': 'H2545', 'faction': 'One', 'player': 'Rik',
                  'x': 40, 'y': 0},
                 {'name': 'Beta', 'type': 'F2551', 'faction': 'Two', 'player': 'Piet',
                  'x': 60, 'y': 0}]
        self._write('ships.jsonl', ships)
        self._write('bodies.jsonl', [{'name': 'Rock', 'type': 'Asteroid', 'x': 120, 'y': 0}])
        admin = AdminService(self.root)
        for who in ('Rik', 'Piet'):
            admin.issue_login(who)
        gd = GameDirectory(self.games, 'terr')
        setup_game(gd)
        for ship in ('Alpha', 'Beta'):
            open(os.path.join(self.games, 'terr', 'commands', f'{ship}-commands-1.txt'), 'w').close()
        Game(gd).process_current_round()
        self.contacts = {c.name: c for c in GameService(self.root).get_player_plan('terr', 'Rik').contacts}

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write(self, name, records):
        with open(os.path.join(self.games, 'terr', name), 'w') as f:
            f.write('\n'.join(json.dumps(r) for r in records) + '\n')

    def test_a_rock_is_neutral_where_a_ship_is_a_foe(self):
        self.assertEqual('Neutral', self.contacts['Rock'].stance)
        self.assertEqual('Foe', self.contacts['Beta'].stance)

    def test_it_carries_its_size_so_the_map_need_not_know_one(self):
        self.assertEqual(40, self.contacts['Rock'].radius)
        self.assertEqual(0, self.contacts['Beta'].radius)


class TestTheRing(TestCase):
    """Factions start on a circle of 500, so the ring goes half way in."""

    def test_five_of_them_evenly_spaced(self):
        ring = FiveFactionWar().bodies()

        self.assertEqual(RING_BODIES, len(ring))
        self.assertEqual({'Asteroid'}, {body['type'] for body in ring})
        for body in ring:
            self.assertAlmostEqual(RING_RADIUS, (body['x'] ** 2 + body['y'] ** 2) ** 0.5, delta=1)

    def test_a_scenario_without_terrain_says_so(self):
        from arena.app.scenarios.generic import GenericGame
        self.assertEqual([], GenericGame().bodies())