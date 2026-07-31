"""The players page: who is offered, and who is folded away."""
import shutil
import tempfile
from unittest import TestCase

from arena.admin_ui import appfacade
from arena.admin_ui.app import app
from arena.app.players import DIRECTOR, LOGIN_COOKIE, PlayerRegistry
from arena.app.services import AdminService

SHIPS = [{'name': 'McAve', 'type': 'F2547', 'faction': 'Three', 'player': 'Menno', 'x': 0, 'y': 0}]


class TestPlayersPage(TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        AdminService(self.root).create_game('mygame', SHIPS)
        self.original, appfacade.GAME_DATA_DIR = appfacade.GAME_DATA_DIR, self.root
        self.registry = PlayerRegistry(self.root)
        self.client = app.test_client()
        self.client.set_cookie(LOGIN_COOKIE, self.registry.issue('Serge', role=DIRECTOR).token)

    def tearDown(self):
        appfacade.GAME_DATA_DIR = self.original
        shutil.rmtree(self.root, ignore_errors=True)

    def page(self) -> str:
        return self.client.get('/players').get_data(as_text=True)

    def one(self, verb: str, name: str):
        """A button on one row carries its player as its own value."""
        return self.client.post('/players/act', data={verb: name})

    def bulk(self, verb: str, *names: str):
        return self.client.post('/players/act', data={'action': verb, 'selected': list(names)})

    def test_everyone_active_is_in_the_main_list(self):
        self.registry.issue('Rik')
        page = self.page()
        self.assertIn('Rik', page)
        self.assertNotIn('Deactivated', page)

    def test_deactivating_moves_them_out_of_the_main_list(self):
        self.registry.issue('Rik')
        self.one('deactivate', 'Rik')
        page = self.page()
        self.assertIn('Deactivated', page)
        self.assertIn('Reactivate', page)

    def test_reactivating_brings_them_back(self):
        self.registry.issue('Rik')
        self.one('deactivate', 'Rik')
        self.one('reactivate', 'Rik')
        page = self.page()
        self.assertNotIn('Deactivated', page)
        self.assertIn(self.registry.by_name('Rik').token, page)

    def test_deactivating_needs_no_confirmation(self):
        self.registry.issue('Rik')
        self.assertNotIn("confirm('Deactivate", self.page())

    def test_a_name_only_a_game_knows_is_not_on_the_list(self):
        # Menno commands a ship in mygame and has never been issued a link. The page is the
        # registry and nothing else, so removing a row really removes it.
        self.assertNotIn('Menno', self.page())

    def test_deactivating_someone_with_no_link_gives_them_a_row(self):
        self.one('deactivate', 'Menno')
        self.assertFalse(self.registry.by_name('Menno').active)
        self.assertIn('Deactivated', self.page())

    def test_removing_takes_the_row_away(self):
        self.registry.issue('Rik')
        self.one('remove', 'Rik')
        self.assertIsNone(self.registry.by_name('Rik'))
        self.assertNotIn('Rik', self.page())

    def test_removing_someone_who_is_in_a_game_still_removes_them(self):
        self.registry.issue('Menno')
        self.one('remove', 'Menno')
        self.assertIsNone(self.registry.by_name('Menno'))
        self.assertNotIn('Menno', self.page())

    def test_removing_a_link_keeps_the_person(self):
        self.registry.issue('Rik')
        self.one('remove_link', 'Rik')
        rik = self.registry.by_name('Rik')
        self.assertEqual('', rik.token)
        self.assertTrue(rik.active)
        self.assertIn('no link yet', self.page())

    def test_a_new_link_keeps_the_role(self):
        before = self.registry.by_name('Serge').token
        self.one('new_link', 'Serge')
        after = self.registry.by_name('Serge')
        self.assertNotEqual(before, after.token)
        self.assertTrue(after.is_director)

    def test_ticked_players_are_deactivated_together(self):
        for name in ('Rik', 'Ilona', 'Dennis'):
            self.registry.issue(name)
        self.bulk('deactivate', 'Rik', 'Ilona')
        self.assertEqual([False, False, True],
                         [self.registry.by_name(n).active for n in ('Rik', 'Ilona', 'Dennis')])

    def test_ticked_players_are_removed_together(self):
        for name in ('Rik', 'Ilona'):
            self.registry.issue(name)
        self.bulk('remove', 'Rik', 'Ilona')
        self.assertEqual(['Serge'], [p.name for p in self.registry.all()])

    def test_ticked_links_are_taken_away_together(self):
        for name in ('Rik', 'Ilona'):
            self.registry.issue(name)
        self.bulk('remove_link', 'Rik', 'Ilona')
        self.assertEqual(['', ''], [self.registry.by_name(n).token for n in ('Rik', 'Ilona')])

    def test_acting_on_the_deactivated_leaves_the_fold_open(self):
        self.registry.issue('Rik')
        self.registry.issue('Ilona')
        self.one('deactivate', 'Rik')
        answer = self.client.post('/players/act',
                                  data={'action': 'reactivate', 'selected': ['Rik'],
                                        'show': 'deactivated'})
        self.assertEqual('/players?show=deactivated', answer.headers['Location'])

    def test_directors_are_listed_apart_from_commanders(self):
        self.registry.issue('Rik')
        page = self.page()
        self.assertLess(page.index('Directors'), page.index('Commanders'))
        self.assertLess(page.index('Serge'), page.index('Commanders'))
        self.assertGreater(page.index('Rik'), page.index('Commanders'))

    def test_a_deactivated_player_is_not_offered_for_a_new_game(self):
        self.registry.issue('Rik')
        self.one('deactivate', 'Rik')
        self.assertNotIn('value="Rik"',
                         self.client.get('/scenario/five-race-war').get_data(as_text=True))