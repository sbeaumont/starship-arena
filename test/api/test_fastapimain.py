"""
Tests for the game API's command endpoints, run against the `apitest` game.

Needs the `test` dependency group (httpx2, for FastAPI's TestClient):
    uv run --group test python -m unittest test.api.test_fastapimain
"""

import unittest

from fastapi.testclient import TestClient

from arena.api.app import app

client = TestClient(app)


class TestCommandsApi(unittest.TestCase):
    def test_add_commands(self):
        commands = {
            'lines': [
                '1: A25',
                '2: Fire R1 90',
                '3:A25',
            ]
        }
        response = client.post('/api/game/apitest/ships/Blaster/commands', json=commands)
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
        response = client.post('/api/game/apitest/ships/Blaster/commands', json=commands)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['ok'])


if __name__ == '__main__':
    unittest.main()
