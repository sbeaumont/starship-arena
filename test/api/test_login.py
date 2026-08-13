"""What the game API lets an unknown, a player and the director do.

Who owns what is read from the game's world, and the access decision is taken before any round
is processed.
"""
import os
import shutil
import tempfile
from unittest import TestCase

from fastapi.testclient import TestClient

from arena.api import game as game_api
from arena.api.app import app
from arena.app.players import DIRECTOR
from arena.app.services import AdminService, GameService

SHIPS = [{'name': 'McAve', 'type': 'F2547', 'faction': 'Three', 'player': 'Menno', 'x': 0, 'y': 0},
         {'name': 'Other', 'type': 'A2527', 'faction': 'One', 'player': 'Rik', 'x': 100, 'y': 0}]


class TestLogin(TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        AdminService(self.root).create_game('mygame', SHIPS, 'generic')
        self.service = GameService(self.root)
        self.original, game_api.service = game_api.service, self.service
        # https, so the client keeps a Secure cookie the way a browser would.
        self.client = TestClient(app, base_url="https://testserver")

    def tearDown(self):
        game_api.service = self.original
        shutil.rmtree(self.root, ignore_errors=True)

    def login_as(self, name, role=''):
        token = self.service.players.issue(name, role=role).token
        return self.client.post('/api/game/login', json={'token': token})

    # ---------------------------------------------------------------- unknown visitor

    def test_no_cookie_is_not_logged_in(self):
        self.assertEqual(401, self.client.get('/api/game/me').status_code)

    def test_the_scoreboard_stays_open(self):
        self.assertEqual(200, self.client.get('/api/game/games').status_code)
        self.assertEqual(200, self.client.get('/api/game/ship-types').status_code)

    def test_a_made_up_token_is_refused(self):
        r = self.client.post('/api/game/login', json={'token': 'not-a-token'})
        self.assertEqual(401, r.status_code)

    def test_a_plan_needs_a_login(self):
        r = self.client.get('/api/game/mygame/players/Menno/plan')
        self.assertEqual(401, r.status_code)

    # ---------------------------------------------------------------- registering

    def test_registering_a_free_name_logs_you_in(self):
        r = self.client.post('/api/game/register', json={'name': 'Newcomer'})
        self.assertEqual(200, r.status_code)
        # No admin_url: the console is not theirs, so they are not told where it is.
        self.assertEqual({'name': 'Newcomer', 'is_director': False, 'games': [], 'admin_url': '',
                          'reminders': {'discord_id': '', 'hours_before': 0,
                                        'daily_hour': None, 'timezone': ''}},
                         r.json())
        self.assertEqual('Newcomer', self.client.get('/api/game/me').json()['name'])

    def test_a_name_that_commands_ships_cannot_be_claimed(self):
        r = self.client.post('/api/game/register', json={'name': 'Menno'})
        self.assertEqual(409, r.status_code)
        self.assertIn('Ask the director', r.json()['detail'])

    def test_a_registered_name_cannot_be_claimed_twice(self):
        self.client.post('/api/game/register', json={'name': 'Newcomer'})
        r = self.client.post('/api/game/register', json={'name': 'Newcomer'})
        self.assertEqual(409, r.status_code)

    # ---------------------------------------------------------------- a player

    def test_a_link_logs_you_in_and_names_your_games(self):
        r = self.login_as('Menno')
        self.assertEqual(200, r.status_code)
        self.assertEqual(['mygame'], r.json()['games'])

    def test_a_player_may_not_see_another_player(self):
        self.login_as('Menno')
        r = self.client.get('/api/game/mygame/players/Rik/plan')
        self.assertEqual(403, r.status_code)

    def test_a_player_may_not_read_another_ship_s_orders(self):
        self.login_as('Menno')
        self.assertEqual(403, self.client.get('/api/game/mygame/ships/Other/commands').status_code)

    def test_a_player_may_not_write_another_ship_s_orders(self):
        self.login_as('Menno')
        r = self.client.post('/api/game/mygame/ships/Other/commands', json={'lines': ['1: A 10']})
        self.assertEqual(403, r.status_code)

    def test_logging_out_forgets_you(self):
        self.login_as('Menno')
        self.client.post('/api/game/logout')
        self.assertEqual(401, self.client.get('/api/game/me').status_code)

    # ---------------------------------------------------------------- the director

    def test_a_replay_is_the_side_you_fly_for(self):
        """Whose it is comes from the cookie, so naming a faction cannot get you somebody else's."""
        self.login_as('Menno')
        body = self.client.get('/api/game/mygame/replay').json()
        self.assertEqual('Three', body['faction'])
        self.assertEqual(['McAve'], [o['name'] for o in body['objects']])

    def test_another_side_is_refused_however_it_is_asked_for(self):
        self.login_as('Menno')
        self.assertEqual(403, self.client.get('/api/game/mygame/replay?faction=One').status_code)

    def test_the_director_replays_a_game_that_has_played_nothing_yet(self):
        self.login_as('Serge', role=DIRECTOR)
        body = self.client.get('/api/game/mygame/replay').json()
        self.assertIsNone(body['faction'])
        self.assertEqual((10, 10), (body['first_tick'], body['last_tick']))
        self.assertEqual(['McAve', 'Other'], sorted(o['name'] for o in body['objects']))

    def test_a_director_watching_as_a_commander_is_filtered_like_one(self):
        """The switch the game UI offers has to reach the API, or the browser holds every side."""
        self.login_as('Menno', role=DIRECTOR)
        self.assertIsNone(self.client.get('/api/game/mygame/replay').json()['faction'])
        body = self.client.get('/api/game/mygame/replay?as_player=true').json()
        self.assertEqual('Three', body['faction'])
        self.assertEqual(['McAve'], [o['name'] for o in body['objects']])

    def test_a_director_who_flies_nothing_has_no_commander_to_watch_as(self):
        self.login_as('Serge', role=DIRECTOR)
        self.assertEqual(403, self.client.get('/api/game/mygame/replay?as_player=true').status_code)

    def test_the_director_is_refused_nothing(self):
        self.login_as('Serge', role=DIRECTOR)
        self.assertTrue(self.client.get('/api/game/me').json()['is_director'])
        # No saved rounds here, so the answer is "no data" rather than "not yours".
        for path in ('/api/game/mygame/players/Rik/plan',
                     '/api/game/mygame/ships/Other/commands'):
            self.assertNotEqual(403, self.client.get(path).status_code, path)