"""The console is the director's: everyone else is turned away."""
import os
import shutil
import tempfile
from unittest import TestCase

from arena.admin_ui import appfacade
from arena.admin_ui.app import app
from arena.app.players import DIRECTOR, LOGIN_COOKIE, PlayerRegistry
from arena.app.services import AdminService

SHIPS = [{'name': 'McAve', 'type': 'F2547', 'faction': 'Three', 'player': 'Menno', 'x': 0, 'y': 0}]


class TestConsoleGate(TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        AdminService(self.root).create_game('mygame', SHIPS, 'generic')
        # The facade reads this when it is built, which is once per request.
        self.original, appfacade.GAME_DATA_DIR = appfacade.GAME_DATA_DIR, self.root
        self.registry = PlayerRegistry(self.root)
        self.client = app.test_client()

    def tearDown(self):
        appfacade.GAME_DATA_DIR = self.original
        shutil.rmtree(self.root, ignore_errors=True)

    def as_(self, name, role=''):
        token = self.registry.issue(name, role=role).token
        self.client.set_cookie(LOGIN_COOKIE, token)
        return token

    def test_a_stranger_is_turned_away(self):
        self.assertEqual(403, self.client.get('/players').status_code)

    def test_a_player_is_turned_away(self):
        self.as_('Menno')
        answer = self.client.get('/players')
        self.assertEqual(403, answer.status_code)
        self.assertIn('Menno', answer.get_data(as_text=True))

    def test_the_director_is_let_in(self):
        self.as_('Serge', role=DIRECTOR)
        self.assertEqual(200, self.client.get('/players').status_code)

    def test_a_director_link_signs_you_in_here_too(self):
        token = self.registry.issue('Serge', role=DIRECTOR).token
        fresh = app.test_client()
        answer = fresh.get(f'/players?login={token}')
        self.assertEqual(302, answer.status_code)
        self.assertEqual('/players', answer.headers['Location'])
        self.assertEqual(200, fresh.get('/players').status_code)

    def test_a_player_s_link_does_not_open_the_console(self):
        token = self.registry.issue('Menno').token
        self.assertEqual(403, app.test_client().get(f'/players?login={token}').status_code)

    def test_the_director_can_issue_and_remove(self):
        self.as_('Serge', role=DIRECTOR)
        self.client.post('/players/issue', data={'name': 'Menno'})
        self.assertIsNotNone(self.registry.by_name('Menno'))
        self.client.post('/players/act', data={'remove': 'Menno'})
        self.assertIsNone(self.registry.by_name('Menno'))

    def test_players_lists_the_registry_and_not_the_rosters(self):
        self.as_('Serge', role=DIRECTOR)
        page = self.client.get('/players').get_data(as_text=True)
        # Menno commands a ship in the game, which is not what puts a name on this page.
        self.assertNotIn('Menno', page)
        self.assertIn('Serge', page)