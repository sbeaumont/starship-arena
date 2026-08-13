"""Valhalla over HTTP, with nobody signed in.

Every other replay route answers 401 to a stranger. These do not, and that is the decision in
docs/gddr/0035-a-finished-game-is-watched-from-any-side.md rather than an oversight.

Needs the `test` dependency group (httpx2, for FastAPI's TestClient):
    uv run --group test python -m unittest test.api.test_valhalla_is_open
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from arena.api import game as game_api
from arena.api.app import app
from arena.app.services import AdminService, GameService

DUEL = [{'name': 'Alpha', 'type': 'H2545', 'faction': 'One', 'player': 'Menno', 'x': 0, 'y': -20},
        {'name': 'Beta', 'type': 'A2527', 'faction': 'Two', 'player': 'Rik', 'x': 0, 'y': 20}]


class TestValhallaIsOpen(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        admin = AdminService(str(self.root))
        service = GameService(str(self.root))
        admin.create_game('duel', DUEL, 'generic')
        service.save_commands('duel', 'Alpha', ['1: Fire L1 Beta'])
        service.save_commands('duel', 'Beta', ['1: Scan'])
        admin.process_turn('duel')
        admin.export_to_valhalla('duel')
        self.original, game_api.service = game_api.service, service
        self.client = TestClient(app, base_url="https://testserver")   # no login, ever

    def tearDown(self):
        game_api.service = self.original
        shutil.rmtree(self.root, ignore_errors=True)

    def test_a_stranger_is_told_what_is_in_there(self):
        listed = self.client.get('/api/game/valhalla').json()
        self.assertEqual(['duel'], [g['name'] for g in listed])
        self.assertEqual(['Menno', 'Rik'], listed[0]['players'])

    def test_a_stranger_may_watch_every_side_at_once(self):
        replay = self.client.get('/api/game/valhalla/duel/replay').json()
        self.assertIsNone(replay['faction'])
        self.assertIn('Alpha', [o['name'] for o in replay['objects']])
        self.assertIn('Beta', [o['name'] for o in replay['objects']])

    def test_a_stranger_may_watch_one_side(self):
        replay = self.client.get('/api/game/valhalla/duel/replay?faction=Two').json()
        self.assertEqual('Two', replay['faction'])
        alpha = next(o for o in replay['objects'] if o['name'] == 'Alpha')
        self.assertTrue(alpha['contact'])       # seen, not known

    def test_the_same_game_still_being_played_is_refused(self):
        self.assertEqual(401, self.client.get('/api/game/duel/replay').status_code)

    def test_a_side_that_never_flew_is_a_bad_request(self):
        self.assertEqual(400,
                         self.client.get('/api/game/valhalla/duel/replay?faction=Nine').status_code)

    def test_a_game_that_is_not_in_there_is_not_found(self):
        self.assertEqual(404, self.client.get('/api/game/valhalla/ghost/replay').status_code)