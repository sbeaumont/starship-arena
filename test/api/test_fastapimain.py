"""
Tests for the game API's command endpoints, run against a copy of the `apitest` game.

A copy, so the test does not move the committed game's state, and its own data root so the
login it needs does not land in the shared registry.

Needs the `test` dependency group (httpx2, for FastAPI's TestClient):
    uv run --group test python -m unittest test.api.test_fastapimain
"""

import os
import shutil
import tempfile
import unittest

from fastapi.testclient import TestClient

from arena.api import game as game_api
from arena.api.app import app
from arena.app.services import GameService

GAME = 'apitest'
SHIP = 'Blaster'
PLAYER = 'Serge'


class TestCommandsApi(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        shutil.copytree(os.path.join('test', 'test-games', GAME), os.path.join(self.root, 'games', GAME))
        self.service = GameService(self.root)
        self.original, game_api.service = game_api.service, self.service
        # https, so the client keeps a Secure cookie the way a browser would.
        self.client = TestClient(app, base_url="https://testserver")
        token = self.service.players.issue(PLAYER).token
        self.client.post('/api/game/login', json={'token': token})

    def tearDown(self):
        game_api.service = self.original
        shutil.rmtree(self.root, ignore_errors=True)

    def test_add_commands(self):
        # Bearing 0 rather than 90: R1 is a bow arc, so a beam shot is refused by validation and
        # this test would be asserting the wrong thing about the route.
        commands = {
            'lines': [
                '1: A25',
                '2: Fire R1 0',
                '3:A25',
            ]
        }
        response = self.client.post(f'/api/game/{GAME}/ships/{SHIP}/commands', json=commands)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])

    def test_add_wrong_commands(self):
        commands = {
            'lines': [
                '1: A40',
                '2: Frrrr R1 90',
                '3:A25',
                '3:A5',
                'flrarlakf',
            ]
        }
        response = self.client.post(f'/api/game/{GAME}/ships/{SHIP}/commands', json=commands)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['ok'])

    def test_commands_are_refused_without_a_login(self):
        anonymous = TestClient(app, base_url="https://testserver")
        response = anonymous.post(f'/api/game/{GAME}/ships/{SHIP}/commands', json={'lines': []})
        self.assertEqual(response.status_code, 401)


if __name__ == '__main__':
    unittest.main()