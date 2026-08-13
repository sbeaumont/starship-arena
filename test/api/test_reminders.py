"""Setting your own reminders, through the player's API."""
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase

from fastapi.testclient import TestClient

from arena.api import game as game_api
from arena.api.app import app
from arena.app.players import LOGIN_COOKIE, PlayerRegistry
from arena.app.services import GameService

OFF = {'discord_id': '', 'hours_before': 0, 'daily_hour': None, 'timezone': ''}


class TestRemindersApi(TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.original = game_api.service
        game_api.service = GameService(str(self.root))
        self.registry = PlayerRegistry(str(self.root))
        self.client = TestClient(app)
        self.client.cookies.set(LOGIN_COOKIE, self.registry.issue('Rik').token)

    def tearDown(self):
        game_api.service = self.original
        shutil.rmtree(self.root, ignore_errors=True)

    def put(self, **asked):
        return self.client.put('/api/game/me/reminders', json={**OFF, **asked})

    def test_a_stranger_may_not_set_anybody_s(self):
        self.assertEqual(401, TestClient(app).put('/api/game/me/reminders', json=OFF).status_code)

    def test_everyone_starts_with_none(self):
        self.assertEqual(OFF, self.client.get('/api/game/me').json()['reminders'])

    def test_setting_both_comes_back_on_me(self):
        answer = self.put(discord_id='4242', hours_before=6,
                          daily_hour=8, timezone='Europe/Amsterdam')
        self.assertEqual(200, answer.status_code)
        self.assertEqual({'discord_id': '4242', 'hours_before': 6,
                          'daily_hour': 8, 'timezone': 'Europe/Amsterdam'},
                         answer.json()['reminders'])
        self.assertEqual(answer.json()['reminders'],
                         self.client.get('/api/game/me').json()['reminders'])

    def test_it_writes_the_caller_s_own_row_and_nobody_else_s(self):
        self.registry.issue('Menno')
        self.put(discord_id='4242', hours_before=6)
        self.assertTrue(self.registry.by_name('Rik').wants_deadline_reminder)
        self.assertFalse(self.registry.by_name('Menno').wants_deadline_reminder)

    def test_turning_one_off_leaves_the_other(self):
        self.put(discord_id='4242', hours_before=6, daily_hour=8, timezone='Europe/Amsterdam')
        answer = self.put(discord_id='4242', daily_hour=8, timezone='Europe/Amsterdam')
        self.assertEqual(0, answer.json()['reminders']['hours_before'])
        self.assertEqual(8, answer.json()['reminders']['daily_hour'])

    def test_midnight_is_an_hour_somebody_can_ask_for(self):
        """Nought is a real answer, so only an absent hour means nobody asked."""
        answer = self.put(discord_id='4242', daily_hour=0, timezone='Europe/Amsterdam')
        self.assertEqual(0, answer.json()['reminders']['daily_hour'])
        self.assertTrue(self.registry.by_name('Rik').wants_daily_reminder)

    def test_a_zone_this_host_never_heard_of_is_refused(self):
        answer = self.put(discord_id='4242', daily_hour=8, timezone='Mars/Olympus')
        self.assertEqual(400, answer.status_code)
        self.assertIn('Mars/Olympus', answer.json()['detail'])

    def test_an_hour_with_no_zone_under_it_is_refused(self):
        self.assertEqual(400, self.put(discord_id='4242', daily_hour=8).status_code)

    def test_an_hour_that_is_not_one_is_refused(self):
        self.assertEqual(400, self.put(discord_id='4242', daily_hour=25,
                                       timezone='Europe/Amsterdam').status_code)

    def test_a_lead_time_before_the_deadline_means_before(self):
        self.assertEqual(400, self.put(discord_id='4242', hours_before=-3).status_code)

    def test_asking_for_nothing_turns_everything_off(self):
        self.put(discord_id='4242', hours_before=6, daily_hour=8, timezone='Europe/Amsterdam')
        self.assertEqual(OFF, self.put().json()['reminders'])
        rik = self.registry.by_name('Rik')
        self.assertFalse(rik.wants_deadline_reminder)
        self.assertFalse(rik.wants_daily_reminder)

    def test_a_new_link_keeps_what_they_set(self):
        self.put(discord_id='4242', hours_before=6)
        self.registry.issue('Rik')
        self.assertTrue(self.registry.by_name('Rik').wants_deadline_reminder)