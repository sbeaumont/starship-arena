"""Putting yourself down for an open game, through the player's API."""
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase

from fastapi.testclient import TestClient

from arena.api import game as game_api
from arena.api.app import app
from arena.app.players import LOGIN_COOKIE, PlayerRegistry
from arena.app.services import AdminService, GameService


class TestRegistrationApi(TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()) / 'games'
        self.root.mkdir()
        self.original = game_api.service
        game_api.service = GameService(str(self.root))
        self.admin = AdminService(str(self.root))
        self.admin.open_registrations('war', 'five-faction-war')
        self.registry = PlayerRegistry(str(self.root))
        self.client = TestClient(app)
        self.client.cookies.set(LOGIN_COOKIE, self.registry.issue('Rik').token)

    def tearDown(self):
        game_api.service = self.original
        shutil.rmtree(self.root.parent, ignore_errors=True)

    def test_a_stranger_is_refused(self):
        self.assertEqual(401, TestClient(app).get('/api/game/open').status_code)

    def test_what_is_open(self):
        answer = self.client.get('/api/game/open')
        self.assertEqual(200, answer.status_code)
        [war] = answer.json()
        self.assertEqual('war', war['name'])
        self.assertEqual('The Five Faction War', war['scenario'])
        self.assertEqual(3, war['max_ships'])
        self.assertEqual([], war['my_ships'])
        self.assertEqual(0, war['players'])

    def test_registering(self):
        answer = self.client.put('/api/game/open/war', json={'names': ['Voyager', 'Pathfinder']})
        self.assertEqual(200, answer.status_code)
        self.assertEqual(['Voyager', 'Pathfinder'], answer.json()['my_ships'])
        self.assertEqual(1, answer.json()['players'])
        self.assertEqual(['Rik'], [e.player for e in self.admin.registrations('war')])

    def test_registering_again_replaces_what_you_asked_for(self):
        self.client.put('/api/game/open/war', json={'names': ['Voyager']})
        answer = self.client.put('/api/game/open/war', json={'names': ['Endeavour', 'Discovery']})
        self.assertEqual(['Endeavour', 'Discovery'], answer.json()['my_ships'])
        self.assertEqual(1, len(self.admin.registrations('war')))

    def test_too_many_ships_is_a_400(self):
        answer = self.client.put('/api/game/open/war', json={'names': ['A', 'B', 'C', 'D']})
        self.assertEqual(400, answer.status_code)
        self.assertIn('3', answer.json()['detail'])

    def test_a_name_somebody_else_took_is_a_400(self):
        self.admin.register('war', 'Menno', ['Voyager'])
        answer = self.client.put('/api/game/open/war', json={'names': ['Voyager']})
        self.assertEqual(400, answer.status_code)
        self.assertIn('Voyager', answer.json()['detail'])

    def test_a_name_that_could_not_be_a_filename_is_a_400(self):
        answer = self.client.put('/api/game/open/war', json={'names': ['../etc/passwd']})
        self.assertEqual(400, answer.status_code)

    def test_blank_names_are_dropped_rather_than_stored(self):
        answer = self.client.put('/api/game/open/war', json={'names': ['Voyager', '  ', '']})
        self.assertEqual(['Voyager'], answer.json()['my_ships'])

    def test_withdrawing(self):
        self.client.put('/api/game/open/war', json={'names': ['Voyager']})
        answer = self.client.delete('/api/game/open/war')
        self.assertEqual([], answer.json()['my_ships'])
        self.assertEqual([], self.admin.registrations('war'))

    def test_somebody_else_s_entry_is_not_yours(self):
        self.admin.register('war', 'Menno', ['Rocinante'])
        [war] = self.client.get('/api/game/open').json()
        self.assertEqual([], war['my_ships'])
        self.assertEqual(1, war['players'])