"""What is written about a game after it is over: the director's synopsis, a commander's story.

The thing worth guarding is that neither is in the exported document. Exporting a game again is
how a schema that has grown reaches a game already in Valhalla, and it must not take the writing
with it. See docs/adr/0036-a-game-in-valhalla-is-written-up.md.
"""
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase

from arena.app.services import AdminService, GameService

DUEL = [{'name': 'Alpha', 'type': 'H2545', 'faction': 'One', 'player': 'Menno', 'x': 0, 'y': -20},
        {'name': 'Beta', 'type': 'A2527', 'faction': 'Two', 'player': 'Rik', 'x': 0, 'y': 20}]


class TestWritingUpAGame(TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.admin = AdminService(str(self.root))
        self.game = GameService(str(self.root))
        self.admin.create_game('duel', DUEL, 'generic')
        self.game.save_commands('duel', 'Alpha', ['1: Fire L1 Beta'])
        self.game.save_commands('duel', 'Beta', ['1: Scan'])
        self.admin.process_turn('duel')
        self.admin.export_to_valhalla('duel')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_the_director_writes_the_synopsis(self):
        self.admin.save_synopsis('duel', '# Short work\n\nOne shot, and it was over.')
        self.assertIn('One shot', self.game.valhalla_game('duel').synopsis)

    def test_a_commander_tells_their_own_side_of_it(self):
        self.game.save_story('duel', 'Rik', 'I never saw it coming.')
        told = self.game.valhalla_game('duel').stories
        self.assertEqual([('Rik', 'I never saw it coming.')], [(s.player, s.text) for s in told])

    def test_a_commander_writing_again_replaces_what_they_said(self):
        self.game.save_story('duel', 'Rik', 'I never saw it coming.')
        self.game.save_story('duel', 'Rik', 'On reflection, I did.')
        told = self.game.valhalla_game('duel').stories
        self.assertEqual(['On reflection, I did.'], [s.text for s in told])

    def test_saving_nothing_takes_a_story_down(self):
        self.game.save_story('duel', 'Rik', 'I never saw it coming.')
        self.game.save_story('duel', 'Rik', '   ')
        self.assertEqual([], self.game.valhalla_game('duel').stories)

    def test_only_the_commanders_of_that_game_may_tell_it(self):
        with self.assertRaises(ValueError):
            self.game.save_story('duel', 'Somebody Else', 'I was there, honest.')

    def test_the_side_that_took_it_says_how(self):
        """Alpha killed Beta, so One took the game and Menno flew for One."""
        self.game.save_win_story('duel', 'Menno', 'We shot first.')
        won = self.game.valhalla_game('duel').win_story
        self.assertEqual(('One', 'Menno', 'We shot first.'), (won.faction, won.player, won.text))

    def test_the_side_that_lost_does_not_say_how_it_was_won(self):
        with self.assertRaises(ValueError):
            self.game.save_win_story('duel', 'Rik', 'We won, actually.')

    def test_the_win_story_is_the_whole_side_s_to_write_over(self):
        """Shared, so the name on it is whoever wrote it last rather than whoever started it."""
        self.game.save_win_story('duel', 'Menno', 'We shot first.')
        self.game.save_win_story('duel', 'Menno', 'We shot first, and we shot straight.')
        self.assertEqual('We shot first, and we shot straight.',
                         self.game.valhalla_game('duel').win_story.text)

    def test_saving_nothing_takes_the_win_story_down(self):
        self.game.save_win_story('duel', 'Menno', 'We shot first.')
        self.game.save_win_story('duel', 'Menno', '')
        self.assertIsNone(self.game.valhalla_game('duel').win_story)

    def test_exporting_the_game_again_leaves_the_writing_alone(self):
        self.admin.save_synopsis('duel', 'One shot, and it was over.')
        self.game.save_story('duel', 'Menno', 'I lined it up and took it.')
        self.game.save_win_story('duel', 'Menno', 'We shot first.')
        self.admin.export_to_valhalla('duel')
        again = self.game.valhalla_game('duel')
        self.assertEqual('One shot, and it was over.', again.synopsis)
        self.assertEqual(['Menno'], [s.player for s in again.stories])
        self.assertEqual('We shot first.', again.win_story.text)

    def test_a_game_nobody_has_written_up_says_so_rather_than_failing(self):
        blank = self.game.valhalla_game('duel')
        self.assertEqual('', blank.synopsis)
        self.assertEqual([], blank.stories)
        self.assertIsNone(blank.win_story)

    def test_the_roster_is_copied_in_beside_the_export(self):
        """Who flew what, in one small file that outlives the game directory."""
        self.assertTrue((self.root / 'valhalla' / 'duel' / 'ships.jsonl').exists())