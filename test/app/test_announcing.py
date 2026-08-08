import os
import shutil
import tempfile
from unittest import TestCase

from arena.announce import Announcer, Channel
from arena.app.dto import By, GameSettings, ProcessingTrigger
from arena.app.services import AdminService, GameService

GAME = 'Deep_Space'

SHIPS = [
    {'name': 'Alpha', 'type': 'A2527', 'faction': 'One', 'player': 'Serge', 'x': 0, 'y': 0},
    {'name': 'Bravo', 'type': 'A2527', 'faction': 'Two', 'player': 'Ilya', 'x': 100, 'y': 100},
]


class Loudspeaker(Channel):
    """A channel that keeps what it was handed, so a test can read it back."""

    def __init__(self, working: bool = True):
        self.heard = []
        self.working = working

    @property
    def name(self) -> str:
        return 'Loudspeaker'

    @property
    def is_configured(self) -> bool:
        return True

    def send(self, message: str) -> None:
        if not self.working:
            raise ConnectionError("nobody home")
        self.heard.append(message)


class TestAnnouncer(TestCase):

    def test_it_says_the_same_thing_on_every_channel(self):
        one, two = Loudspeaker(), Loudspeaker()
        Announcer([one, two]).announce("Round 3 is out")
        self.assertEqual(["Round 3 is out"], one.heard)
        self.assertEqual(["Round 3 is out"], two.heard)

    def test_a_channel_without_an_address_is_not_asked(self):
        self.assertEqual([], Announcer([]).configured)

    def test_one_channel_failing_does_not_stop_the_next(self):
        broken, working = Loudspeaker(working=False), Loudspeaker()
        Announcer([broken, working]).announce("Round 3 is out")
        self.assertEqual(["Round 3 is out"], working.heard)


class TestAnnouncingARound(TestCase):
    """Every way of processing a round announces it, and the game says whether it does."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.speaker = Loudspeaker()
        self.admin = AdminService(self.root, announcer=Announcer([self.speaker]))
        self.game = GameService(self.root, announcer=Announcer([self.speaker]))
        self.admin.create_game(GAME, SHIPS)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _order_up(self):
        for ship in ('Alpha', 'Bravo'):
            self.game.save_commands(GAME, ship, ['turn 10'])

    def test_a_new_game_announces_by_default(self):
        self.assertTrue(self.admin.settings(GAME).announce)

    def test_the_director_processing_announces(self):
        self._order_up()
        self.admin.process_turn(GAME)
        self.assertEqual(1, len(self.speaker.heard))
        self.assertIn('round 1', self.speaker.heard[0])
        self.assertIn('Deep Space', self.speaker.heard[0])

    def test_forcing_a_round_announces(self):
        self.admin.force_process_turn(GAME, By.DIRECTOR, ProcessingTrigger.MANUAL_FORCED)
        self.assertEqual(1, len(self.speaker.heard))

    def test_the_last_player_saying_ready_announces(self):
        self.admin.save_settings(GAME, GameSettings(on_all_ready=True, process_hours=[]))
        self._order_up()
        self.game.set_ready(GAME, 'Serge', True)
        self.assertEqual([], self.speaker.heard)
        self.game.set_ready(GAME, 'Ilya', True)
        self.assertEqual(1, len(self.speaker.heard))

    def test_a_game_told_not_to_announce_stays_quiet(self):
        self.admin.save_settings(GAME, GameSettings(on_all_ready=False, process_hours=[],
                                                    announce=False))
        self._order_up()
        self.admin.process_turn(GAME)
        self.assertEqual([], self.speaker.heard)

    def test_regenerating_announces_nothing(self):
        self._order_up()
        self.admin.process_turn(GAME)
        self.speaker.heard.clear()
        self.admin.regenerate_game(GAME)
        self.assertEqual([], self.speaker.heard)