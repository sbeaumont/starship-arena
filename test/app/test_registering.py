"""A game that has been named and is collecting registrations, but has not started."""
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase

from arena.app.dto import GameSettings
from arena.app.services import AdminService


class TestRegisteringGames(TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.admin = AdminService(str(self.root))
        self.admin.open_registrations('war', 'five-faction-war')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def register_four(self):
        for player, names in (('Rik', ['Voyager', 'Pathfinder']), ('Menno', ['Rocinante']),
                              ('Ilona', ['Nauvoo']), ('Dennis', ['Tachi'])):
            self.admin.register('war', player, names)

    def test_it_is_not_a_game_being_played_yet(self):
        self.assertEqual([], [g.name for g in self.admin.list_games()])
        self.assertEqual(['war'], [g.name for g in self.admin.list_registering_games()])

    def test_it_holds_its_scenario(self):
        self.assertEqual('five-faction-war', self.admin.scenario_of('war'))

    def test_the_name_is_claimed_while_it_registers(self):
        self.assertIn('war', self.admin.game_names_in_use())
        with self.assertRaises(ValueError):
            self.admin.open_registrations('war', 'five-faction-war')

    def test_an_unknown_scenario_is_refused(self):
        with self.assertRaises(KeyError):
            self.admin.open_registrations('other', 'no-such-war')

    def test_registering_and_reading_back(self):
        self.admin.register('war', 'Rik', ['Voyager', 'Pathfinder'])
        self.assertEqual([('Rik', 2)], [(e.player, e.ships) for e in self.admin.registrations('war')])

    def test_the_scenario_sets_the_ship_limit(self):
        with self.assertRaises(ValueError):
            self.admin.register('war', 'Rik', ['A', 'B', 'C', 'D'])

    def test_withdrawing(self):
        self.admin.register('war', 'Rik', ['Voyager'])
        self.admin.withdraw('war', 'Rik')
        self.assertEqual([], self.admin.registrations('war'))

    def test_starting_moves_the_directory_into_play(self):
        self.register_four()
        ships = [{'name': 'Voyager', 'type': 'H2545', 'faction': 'Human', 'player': 'Rik'}]
        self.admin.start_game('war', ships, GameSettings(on_all_ready=True, process_hours=[8]))

        self.assertEqual(['war'], [g.name for g in self.admin.list_games()])
        self.assertEqual([], self.admin.list_registering_games())
        self.assertFalse((self.root / 'registering' / 'war').exists())

    def test_starting_writes_the_roster_and_the_settings(self):
        self.register_four()
        ships = [{'name': 'Voyager', 'type': 'H2545', 'faction': 'Human', 'player': 'Rik'}]
        self.admin.start_game('war', ships, GameSettings(on_all_ready=True, process_hours=[8, 20]))

        self.assertTrue((self.root / 'games' / 'war' / 'ships.jsonl').exists())
        self.assertEqual(GameSettings(on_all_ready=True, process_hours=[8, 20]),
                         self.admin.settings('war'))

    def test_the_registrations_travel_with_it(self):
        self.register_four()
        ships = [{'name': 'Voyager', 'type': 'H2545', 'faction': 'Human', 'player': 'Rik'}]
        self.admin.start_game('war', ships, GameSettings(on_all_ready=False, process_hours=[]))
        self.assertTrue((self.root / 'games' / 'war' / 'registrations.jsonl').exists())

    def test_starting_over_a_live_game_is_refused(self):
        (self.root / 'games' / 'war').mkdir(parents=True)
        with self.assertRaises(ValueError):
            self.admin.start_game('war', [], GameSettings(on_all_ready=False, process_hours=[]))

    def start_it(self):
        self.register_four()
        ships = [{'name': 'Voyager', 'type': 'H2545', 'faction': 'Human', 'player': 'Rik'}]
        self.admin.start_game('war', ships, GameSettings(on_all_ready=False, process_hours=[]))

    def test_a_started_game_can_go_back_into_registration(self):
        self.start_it()
        self.assertTrue(self.admin.is_reopenable('war'))
        self.admin.reopen_registrations('war')
        self.assertEqual(['war'], [g.name for g in self.admin.list_registering_games()])
        self.assertEqual([], self.admin.list_games())
        self.assertEqual(4, len(self.admin.registrations('war')))
        self.assertFalse((self.root / 'registering' / 'war' / 'ships.jsonl').exists())

    def test_a_game_that_has_played_a_round_cannot(self):
        self.start_it()
        (self.root / 'games' / 'war' / 'status_round_1.pickle').write_text('not really')
        self.assertFalse(self.admin.is_reopenable('war'))
        with self.assertRaises(ValueError):
            self.admin.reopen_registrations('war')

    def test_a_game_that_never_had_registrations_cannot(self):
        self.admin.create_game('handmade',
                               [{'name': 'A', 'type': 'H2545', 'faction': 'Human'}])
        self.assertFalse(self.admin.is_reopenable('handmade'))
        with self.assertRaises(ValueError):
            self.admin.reopen_registrations('handmade')
