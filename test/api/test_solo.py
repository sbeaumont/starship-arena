"""Starting and playing a game of your own, over the API a shared game is played through."""
import shutil
import tempfile
from unittest import TestCase

from fastapi.testclient import TestClient

from arena.api import game as game_api
from arena.api.app import app
from arena.app.services import GameService

PICK = {'ships': [{'name': 'Rocinante', 'type': 'H2545'}]}


class TestSoloOverTheApi(TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.service = GameService(self.root)
        self.original, game_api.service = game_api.service, self.service
        self.client = TestClient(app, base_url="https://testserver")

    def tearDown(self):
        game_api.service = self.original
        shutil.rmtree(self.root, ignore_errors=True)

    def login_as(self, name):
        self.client.post('/api/game/login',
                         json={'token': self.service.players.issue(name).token})

    def test_it_needs_a_login(self):
        self.assertEqual(401, self.client.get('/api/game/solo').status_code)
        self.assertEqual(401, self.client.post('/api/game/solo', json=PICK).status_code)

    def test_the_offer_before_anybody_has_started_one(self):
        self.login_as('Menno')
        body = self.client.get('/api/game/solo').json()
        self.assertIsNone(body['game'])
        self.assertEqual(2, body['max_ships'])
        self.assertTrue(body['blurb'])

    def test_starting_one_and_reading_it_back(self):
        self.login_as('Menno')
        started = self.client.post('/api/game/solo', json=PICK)
        self.assertEqual(200, started.status_code)
        self.assertEqual('Solo_Menno', started.json()['game']['name'])
        self.assertEqual('Solo Menno', started.json()['game']['display'])
        self.assertEqual(started.json(), self.client.get('/api/game/solo').json())

    def test_it_is_planned_through_the_ordinary_routes(self):
        self.login_as('Menno')
        self.client.post('/api/game/solo', json=PICK)

        plan = self.client.get('/api/game/Solo_Menno/players/Menno/plan')
        self.assertEqual(200, plan.status_code)
        self.assertEqual(['Rocinante'], [s['name'] for s in plan.json()['ships']])

        saved = self.client.post('/api/game/Solo_Menno/ships/Rocinante/commands',
                                 json={'lines': ['1: Accelerate 20']})
        self.assertTrue(saved.json()['ok'])

    def test_saying_ready_processes_the_round(self):
        self.login_as('Menno')
        self.client.post('/api/game/solo', json=PICK)
        self.client.post('/api/game/Solo_Menno/ships/Rocinante/commands',
                         json={'lines': ['1: Accelerate 20']})

        ready = self.client.post('/api/game/Solo_Menno/players/Menno/ready', json={'ready': True})
        self.assertEqual({'ready': False, 'processed': True}, ready.json())
        self.assertEqual(2, self.client.get('/api/game/solo').json()['game']['current_round'])

    def test_it_stays_out_of_the_games_list(self):
        self.login_as('Menno')
        self.client.post('/api/game/solo', json=PICK)
        self.assertEqual([], self.client.get('/api/game/games').json())
        self.assertEqual([], self.client.get('/api/game/me').json()['games'])

    def test_it_is_yours_and_nobody_else_s(self):
        self.login_as('Menno')
        self.client.post('/api/game/solo', json=PICK)
        self.login_as('Rik')
        self.assertIsNone(self.client.get('/api/game/solo').json()['game'])
        self.assertEqual(403,
                         self.client.get('/api/game/Solo_Menno/players/Menno/plan').status_code)

    def test_a_pick_it_refuses(self):
        self.login_as('Menno')
        r = self.client.post('/api/game/solo', json={'ships': [{'name': 'Base', 'type': 'SB2531'}]})
        self.assertEqual(400, r.status_code)
        self.assertIn('SB2531', r.json()['detail'])