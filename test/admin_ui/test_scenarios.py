"""Dealing a scenario's roster, and the two screens that do it."""
import json
import random
import shutil
import tempfile
from collections import Counter
from pathlib import Path
from unittest import TestCase

from arena.admin_ui import appfacade
from arena.admin_ui.app import app
from arena.app.registrations import Registration
from arena.app.scenarios import by_key
from arena.app.scenarios.five_faction_war import FACTIONS, STARBASE
from arena.app.players import DIRECTOR, LOGIN_COOKIE, PlayerRegistry
from arena.app.services import AdminService

ALL_FIVE = list(FACTIONS)


def entries(*specs) -> list[Registration]:
    """('Rik', 2) is Rik asking for two ships; a bare 'Rik' asks for one."""
    asked = [(s, 1) if isinstance(s, str) else s for s in specs]
    return [Registration(player=who, names=[f'{who}-{n}' for n in range(1, count + 1)])
            for who, count in asked]


class TestDealing(TestCase):
    def setUp(self):
        self.scenario = by_key('five-faction-war')
        self.rng = random.Random(4)

    def deal(self, people):
        return self.scenario.deal(people, self.rng)

    @staticmethod
    def over(people, *factions) -> list:
        """Assign everybody by hand, so only these factions end up in the game."""
        for i, entry in enumerate(people):
            entry.faction = factions[i % len(factions)]
        return people

    @staticmethod
    def put(people, **factions) -> list:
        """Assign the named ones and leave the rest in the pool."""
        for entry in people:
            entry.faction = factions.get(entry.player, '')
        return people

    @staticmethod
    def ships_per_faction(records) -> Counter:
        return Counter(r['faction'] for r in records if r['type'] != STARBASE)

    def test_everybody_gets_a_ship(self):
        records = self.deal(entries('Rik', 'Menno', 'Serge', 'Dennis', 'Ilona'))
        self.assertEqual({'Rik', 'Menno', 'Serge', 'Dennis', 'Ilona'},
                         {r['player'] for r in records if r['type'] != STARBASE})

    def test_every_faction_gets_one_starbase_with_a_commander(self):
        records = self.deal(entries('Rik', 'Menno', 'Serge', 'Dennis', 'Ilona'))
        bases = [r for r in records if r['type'] == STARBASE]
        self.assertEqual(sorted(ALL_FIVE), sorted(r['faction'] for r in bases))
        self.assertTrue(all(r['player'] for r in bases))

    def test_the_starbase_goes_to_someone_in_its_own_faction(self):
        records = self.deal(entries(*[f'P{n}' for n in range(12)]))
        crew = {f: {r['player'] for r in records
                    if r['faction'] == f and r['type'] != STARBASE} for f in ALL_FIVE}
        for base in [r for r in records if r['type'] == STARBASE]:
            self.assertIn(base['player'], crew[base['faction']])

    def test_names_are_unique(self):
        names = [r['name'] for r in self.deal(entries(*[f'P{n}' for n in range(17)]))]
        self.assertEqual(len(names), len(set(names)))

    def test_a_player_s_own_names_are_used(self):
        records = self.deal(self.over([Registration('Rik', ['Voyager', 'Pathfinder']),
                                       Registration('Menno', ['Rocinante', 'Nauvoo'])],
                                      'Human', 'Feline'))
        mine = sorted(r['name'] for r in records if r['player'] == 'Rik' and r['type'] != STARBASE)
        self.assertEqual(['Pathfinder', 'Voyager'], mine)

    def test_hulls_come_from_the_faction_s_own_line(self):
        records = self.deal(entries(*[f'P{n}' for n in range(20)]))
        for record in records:
            if record['type'] != STARBASE:
                self.assertIn(record['type'], FACTIONS[record['faction']])

    def test_a_faction_flies_more_than_one_hull(self):
        people = entries(*[f'P{n}' for n in range(20)])
        records = self.deal(self.over(people, 'Human', 'Feline'))
        for faction in ('Human', 'Feline'):
            hulls = {r['type'] for r in records if r['faction'] == faction and r['type'] != STARBASE}
            self.assertGreater(len(hulls), 1)

    def test_factions_come_out_level_when_everyone_wants_one(self):
        records = self.deal(entries(*[f'P{n}' for n in range(20)]))
        self.assertEqual([4] * 5, sorted(self.ships_per_faction(records).values()))

    def test_everybody_gets_every_ship_they_registered(self):
        people = entries(('Rik', 3), ('Menno', 1), ('Serge', 2), ('Ilona', 1))
        records = self.deal(self.over(people, 'Human', 'Feline'))
        got = Counter(r['player'] for r in records if r['type'] != STARBASE)
        for entry in people:
            self.assertEqual(entry.ships, got[entry.player])

    def test_a_lopsided_faction_stays_lopsided(self):
        # Rik's three are not cut back to what Menno's faction can field. The director balances.
        people = entries(('Rik', 3), ('Menno', 1))
        records = self.deal(self.over(people, 'Human', 'Feline'))
        self.assertEqual([1, 3], sorted(self.ships_per_faction(records).values()))

    def test_faction_sizes_differ_by_at_most_one(self):
        records = self.deal(entries(*[f'P{n}' for n in range(13)]))
        crews = [len({r['player'] for r in records if r['faction'] == f}) for f in ALL_FIVE]
        self.assertLessEqual(max(crews) - min(crews), 1)

    def test_a_faction_nobody_lands_in_is_not_in_the_game(self):
        records = self.deal(entries('Rik', 'Menno'))
        self.assertEqual(2, len({r['faction'] for r in records}))

    def test_the_assigned_stay_where_they_were_put(self):
        people = entries('Rik', 'Menno', 'Serge', 'Dennis', 'Ilona')
        records = self.deal(self.put(people, Rik='Insectoid', Menno='Insectoid'))
        mine = {r['player']: r['faction'] for r in records if r['type'] != STARBASE}
        self.assertEqual('Insectoid', mine['Rik'])
        self.assertEqual('Insectoid', mine['Menno'])

    def test_the_pool_evens_the_numbers_out_around_them(self):
        people = entries(*[f'P{n}' for n in range(12)])
        records = self.deal(self.put(people, P0='Human', P1='Human', P2='Human'))
        crews = Counter(r['player'] for r in records if r['type'] != STARBASE)
        by_faction = {}
        for r in records:
            if r['type'] != STARBASE:
                by_faction.setdefault(r['faction'], set()).add(r['player'])
        sizes = sorted(len(s) for s in by_faction.values())
        self.assertEqual(3, max(sizes))
        self.assertGreaterEqual(min(sizes), 2)
        self.assertEqual(12, len(crews))

    def test_nobody_registered_raises(self):
        with self.assertRaises(ValueError):
            self.deal([])

    def test_an_unknown_faction_raises(self):
        with self.assertRaises(ValueError):
            self.deal(self.put(entries('Rik', 'Menno', 'Serge'), Rik='Klingon'))

    def test_nothing_is_placed(self):
        for record in self.deal(entries('Rik', 'Menno', 'Serge', 'Dennis', 'Ilona')):
            self.assertNotIn('x', record)
            self.assertNotIn('y', record)


class TestConsoleFlow(TestCase):
    """Open registrations, assign them into factions, start the game."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp()) / 'games'
        self.root.mkdir()
        self.original, appfacade.GAME_DATA_DIR = appfacade.GAME_DATA_DIR, str(self.root)
        registry = PlayerRegistry(str(self.root))
        self.client = app.test_client()
        self.client.set_cookie(LOGIN_COOKIE, registry.issue('Serge', role=DIRECTOR).token)
        self.admin = AdminService(str(self.root))

    def tearDown(self):
        appfacade.GAME_DATA_DIR = self.original
        shutil.rmtree(self.root.parent, ignore_errors=True)

    def open_war(self):
        self.client.post('/new_game', data={'game_name': 'war', 'scenario': 'five-faction-war'})

    def register_four(self):
        for player, names in (('Rik', ['Voyager', 'Pathfinder']), ('Menno', ['Rocinante']),
                              ('Ilona', ['Nauvoo']), ('Dennis', ['Tachi'])):
            self.admin.register('war', player, names)

    def test_the_list_offers_the_five_faction_war(self):
        page = self.client.get('/new_game').get_data(as_text=True)
        self.assertIn('Five Faction War', page)
        self.assertIn('value="five-faction-war"', page)

    def test_opening_registrations_lands_on_the_assign_screen(self):
        answer = self.client.post('/new_game',
                                  data={'game_name': 'war', 'scenario': 'five-faction-war'})
        self.assertEqual(302, answer.status_code)
        self.assertEqual('/registering/war', answer.headers['Location'])
        self.assertEqual(['war'], [g.name for g in self.admin.list_registering_games()])

    def test_a_name_already_in_use_is_refused(self):
        self.open_war()
        page = self.client.post('/new_game',
                                data={'game_name': 'war',
                                      'scenario': 'five-faction-war'}).get_data(as_text=True)
        self.assertIn('already exists', page)

    def test_a_bad_game_name_is_refused(self):
        page = self.client.post('/new_game',
                                data={'game_name': '9lives',
                                      'scenario': 'five-faction-war'}).get_data(as_text=True)
        self.assertIn('must be a letter', page)
        self.assertEqual([], self.admin.list_registering_games())

    def test_an_open_game_is_listed(self):
        self.open_war()
        page = self.client.get('/registering').get_data(as_text=True)
        self.assertIn('/registering/war', page)

    def test_an_unknown_game_is_a_404(self):
        self.assertEqual(404, self.client.get('/registering/nothing').status_code)

    def test_the_assign_screen_shows_every_registration(self):
        self.open_war()
        self.register_four()
        page = self.client.get('/registering/war').get_data(as_text=True)
        for player in ('Rik', 'Menno', 'Ilona', 'Dennis'):
            self.assertIn(f'data-player="{player}"', page)
        self.assertIn('Voyager · Pathfinder', page)
        for faction in ALL_FIVE:
            self.assertIn(f'data-faction="{faction}"', page)

    def test_an_empty_signup_says_so(self):
        self.open_war()
        self.assertIn('Nobody has registered',
                      self.client.get('/registering/war').get_data(as_text=True))

    def test_dealing_lands_on_the_roster_screen_ready_to_start(self):
        self.open_war()
        self.register_four()
        answer = self.client.post('/registering/war',
                                  data={'player': ['Rik', 'Menno'],
                                        'faction': ['Human', 'Feline'], 'next': '1'})
        page = answer.get_data(as_text=True)
        self.assertEqual(200, answer.status_code)
        self.assertIn('Start game', page)
        self.assertIn('/start/war', page)
        self.assertIn('name="on_all_ready"', page)
        self.assertIn('Voyager', page)

    def test_the_assigned_land_where_they_were_put(self):
        self.open_war()
        self.register_four()
        page = self.client.post('/registering/war',
                                data={'player': ['Rik', 'Menno', 'Ilona', 'Dennis'],
                                      'faction': ['Human', 'Human', 'Feline', 'Feline'],
                                      'next': '1'}).get_data(as_text=True)
        # Two factions only, so two starbases and no third faction anywhere.
        self.assertEqual(2, page.count('value="SB2531" selected>'))

    def test_starting_creates_the_game_with_its_settings(self):
        self.open_war()
        self.register_four()
        self.admin.assign('war', {'Rik': 'Human', 'Menno': 'Feline'})
        records = by_key('five-faction-war').deal(self.admin.registrations('war'), random.Random(1))
        answer = self.client.post('/start/war', data={
            'ship_name': [r['name'] for r in records],
            'ship_type': [r['type'] for r in records],
            'ship_faction': [r['faction'] for r in records],
            'ship_player': [r['player'] for r in records],
            'ship_x': [''] * len(records),
            'ship_y': [''] * len(records),
            'on_all_ready': '1',
            'hour': ['8', '20']})
        self.assertEqual(302, answer.status_code)

        self.assertEqual(['war'], [g.name for g in self.admin.list_games()])
        self.assertEqual([], self.admin.list_registering_games())
        settings = self.admin.settings('war')
        self.assertTrue(settings.on_all_ready)
        self.assertEqual([8, 20], settings.process_hours)

        written = [json.loads(line) for line in
                   (self.root / 'war' / 'ships.jsonl').read_text().splitlines()]
        self.assertEqual(sorted(r['name'] for r in records),
                         sorted(s['name'] for s in written))
        self.assertTrue(any(s['x'] or s['y'] for s in written))

    def test_the_registrations_survive_the_start(self):
        self.open_war()
        self.register_four()
        records = by_key('five-faction-war').deal(self.admin.registrations('war'), random.Random(1))
        self.client.post('/start/war', data={
            'ship_name': [r['name'] for r in records],
            'ship_type': [r['type'] for r in records],
            'ship_faction': [r['faction'] for r in records],
            'ship_player': [r['player'] for r in records],
            'ship_x': [''] * len(records),
            'ship_y': [''] * len(records)})
        self.assertTrue((self.root / 'war' / 'registrations.jsonl').exists())

    def test_a_broken_roster_comes_back_with_the_problem(self):
        self.open_war()
        self.register_four()
        page = self.client.post('/start/war', data={
            'ship_name': ['Voyager'], 'ship_type': ['NOPE'], 'ship_faction': ['Human'],
            'ship_player': ['Rik'], 'ship_x': [''], 'ship_y': ['']}).get_data(as_text=True)
        self.assertIn('not a known ship type', page)
        self.assertEqual([], self.admin.list_games())

    def test_saving_an_assignment_keeps_it_and_stays_put(self):
        self.open_war()
        self.register_four()
        answer = self.client.post('/registering/war',
                                  data={'player': ['Rik', 'Menno'],
                                        'faction': ['Human', 'Feline']})
        self.assertEqual(200, answer.status_code)
        self.assertIn('Not assigned', answer.get_data(as_text=True))
        saved = {e.player: e.faction for e in self.admin.registrations('war')}
        self.assertEqual({'Rik': 'Human', 'Menno': 'Feline', 'Ilona': '', 'Dennis': ''}, saved)

    def test_a_saved_assignment_comes_back_in_its_column(self):
        self.open_war()
        self.register_four()
        self.admin.assign('war', {'Rik': 'Insectoid'})
        page = self.client.get('/registering/war').get_data(as_text=True)
        insectoid = page.split('data-faction="Insectoid"')[1]
        self.assertIn('data-player="Rik"', insectoid.split('</div>')[0] + insectoid[:200])

    def test_dragging_somebody_back_to_the_pool_clears_them(self):
        self.open_war()
        self.register_four()
        self.admin.assign('war', {'Rik': 'Human', 'Menno': 'Feline'})
        self.client.post('/registering/war', data={'player': ['Menno'], 'faction': ['Feline']})
        saved = {e.player: e.faction for e in self.admin.registrations('war')}
        self.assertEqual('', saved['Rik'])
        self.assertEqual('Feline', saved['Menno'])

    def test_the_registering_list_counts_players_and_ships(self):
        self.open_war()
        self.register_four()
        self.admin.assign('war', {'Rik': 'Human'})
        page = self.client.get('/registering').get_data(as_text=True)
        self.assertIn('The Five Faction War', page)
        self.assertIn('>4<', page)          # four players
        self.assertIn('>5<', page)          # five ships between them
        self.assertIn('1 of 4', page)       # one of them assigned

    def test_the_roster_offers_only_this_game_s_players(self):
        self.open_war()
        self.register_four()
        page = self.client.post('/registering/war', data={'next': '1'}).get_data(as_text=True)
        options = page.split('id="known-players"')[1].split('</datalist>')[0]
        for player in ('Rik', 'Menno', 'Ilona', 'Dennis'):
            self.assertIn(f'value="{player}"', options)
        self.assertNotIn('value="Serge"', options)

    def test_the_roster_can_go_back_to_the_assignment(self):
        self.open_war()
        self.register_four()
        page = self.client.post('/registering/war', data={'next': '1'}).get_data(as_text=True)
        self.assertIn('/registering/war', page)

    def test_a_generic_game_goes_straight_to_a_roster(self):
        answer = self.client.post('/new_game', data={'game_name': 'Hand Made',
                                                     'scenario': 'generic'})
        page = answer.get_data(as_text=True)
        self.assertEqual(200, answer.status_code)
        self.assertIn('Create game', page)
        self.assertIn('Hand Made', page)
        self.assertEqual([], self.admin.list_registering_games())

    def test_a_generic_game_is_created_from_its_roster(self):
        self.client.post('/roster', data={
            'game_name': 'Hand Made', 'ship_name': ['Blaster'], 'ship_type': ['H2545'],
            'ship_faction': ['One'], 'ship_player': ['Serge'], 'ship_x': [''], 'ship_y': ['']})
        self.assertEqual(['Hand_Made'], [g.name for g in self.admin.list_games()])
