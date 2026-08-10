"""A game a player starts and plays on their own, in a root of its own."""
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase

from arena.app.scenarios.solo import OPPOSITION, PLAYER_FACTION, SPOTS
from arena.app.services import AdminService, GameService

PICK = [{'name': 'Rocinante', 'type': 'H2545'}]


class TestSoloGames(TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.game = GameService(str(self.root))
        self.admin = AdminService(str(self.root))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def start(self, player='Menno', picks=None):
        return self.game.start_solo_game(player, picks if picks is not None else PICK)

    def test_a_player_has_none_until_they_start_one(self):
        offer = self.game.solo_game('Menno')
        self.assertIsNone(offer.game)
        self.assertEqual(2, offer.max_ships)

    def test_starting_one_puts_it_in_the_solo_root(self):
        offer = self.start()
        self.assertEqual('Solo_Menno', offer.game.name)
        self.assertTrue((self.root / 'solo-games' / 'Solo_Menno').is_dir())
        self.assertFalse((self.root / 'games' / 'Solo_Menno').exists())

    def test_a_name_with_a_dot_in_it_is_a_directory_name(self):
        offer = self.start('St. Nicolaas')
        self.assertEqual('Solo_St._Nicolaas', offer.game.name)
        self.assertEqual('Solo St. Nicolaas', offer.game.display)

    def test_it_is_not_one_of_the_shared_games(self):
        self.start()
        self.assertEqual([], self.game.list_games())
        self.assertEqual([], self.game.games_for_player('Menno'))
        self.assertEqual(['Solo_Menno'], [g.name for g in self.game.list_solo_games()])

    def test_the_name_is_claimed_all_the_same(self):
        self.start()
        self.assertIn('Solo_Menno', self.admin.game_names_in_use())

    def test_the_roster_is_the_pick_and_three_pirates(self):
        name = self.start().game.name
        plan = self.game.get_player_plan(name, 'Menno')
        self.assertEqual(['Rocinante'], [s.name for s in plan.ships])
        self.assertEqual([PLAYER_FACTION], plan.factions)

        world = self.game._gd(name).load_world(0)
        pirates = [o for o in world.objects.values() if o.faction == OPPOSITION]
        self.assertEqual(3, len(pirates))
        self.assertEqual(set(SPOTS[OPPOSITION]), {(p.pos.x, p.pos.y) for p in pirates})
        self.assertEqual([''], list({p.player for p in pirates}))

    def test_the_standard_five_asteroids_are_always_there(self):
        name = self.start().game.name
        world = self.game._gd(name).load_world(0)
        rocks = [o for o in world.objects.values() if o.category_name == 'Terrain']
        self.assertEqual(5, len(rocks))
        self.assertIn((0, 250), [(r.pos.x, r.pos.y) for r in rocks])

    def test_the_player_starts_below_the_asteroids_looking_at_them(self):
        name = self.start().game.name
        world = self.game._gd(name).load_world(0)
        mine = world.objects['Rocinante']
        self.assertEqual(SPOTS[PLAYER_FACTION][0], (mine.pos.x, mine.pos.y))
        self.assertEqual(0, mine.heading)

    def test_saying_ready_processes_the_round_on_the_spot(self):
        name = self.start().game.name
        self.game.save_commands(name, 'Rocinante', ['1: Accelerate 20'])

        self.assertTrue(self.game.set_ready(name, 'Menno', True))
        self.assertEqual(2, self.game.solo_game('Menno').game.current_round)

    def test_nothing_is_announced_and_no_hour_is_kept(self):
        name = self.start().game.name
        settings = self.game.settings(name)
        self.assertTrue(settings.on_all_ready)
        self.assertEqual([], settings.process_hours)
        self.assertFalse(settings.announce)

    def test_starting_another_replaces_the_one_they_had(self):
        name = self.start().game.name
        self.game.save_commands(name, 'Rocinante', ['1: Accelerate 20'])
        self.game.set_ready(name, 'Menno', True)

        again = self.start(picks=[{'name': 'Nauvoo', 'type': 'R2545'}])
        self.assertEqual(name, again.game.name)
        self.assertEqual(1, again.game.current_round)
        self.assertEqual(['Nauvoo'], [s.name for s in self.game.get_player_plan(name, 'Menno').ships])
        self.assertEqual(['Solo_Menno'], sorted(p.name for p in (self.root / 'solo-games').iterdir()))

    def test_two_players_each_have_their_own(self):
        self.start('Menno')
        self.start('Rik', [{'name': 'Voyager', 'type': 'F2551'}])
        self.assertEqual(['Solo_Menno', 'Solo_Rik'],
                         [g.name for g in self.game.list_solo_games()])
        self.assertEqual('Solo_Rik', self.game.solo_game('Rik').game.name)

    def test_a_shared_game_may_not_take_a_solo_name(self):
        """Reserved as a set, so a name clash cannot arise and nothing has to resolve one."""
        roster = [{'name': 'Other', 'type': 'H2545', 'faction': 'One', 'player': 'Menno'}]
        for name in ('Solo_Menno', 'Solo_Nobody', 'Solo Mission'):
            with self.subTest(name):
                with self.assertRaises(ValueError):
                    self.admin.create_game(name, roster, 'generic')
                with self.assertRaises(ValueError):
                    self.admin.open_registrations(name, 'generic')

    def test_what_it_refuses(self):
        for picks, why in (([], 'no ships'),
                           (PICK * 3, 'more than the scenario allows'),
                           ([{'name': '  ', 'type': 'H2545'}], 'a blank name'),
                           ([{'name': 'Base', 'type': 'SB2531'}], 'a starbase'),
                           ([{'name': f'{OPPOSITION}-1', 'type': 'H2545'}], 'a name in use')):
            with self.subTest(why):
                with self.assertRaises(ValueError):
                    self.start(picks=picks)