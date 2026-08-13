import json
import os
import shutil
import tempfile
from datetime import timedelta
from unittest import TestCase

from arena.announce import Announcer
from arena.app.clock import next_occurrence, server_now
from arena.app.dto import GameSettings
from arena.app.services import AdminService, GameService
from arena.cfg import PLAYERS_FILE_NAME
from test.app.test_announcing import Loudspeaker

GAME = 'Deep_Space'

SHIPS = [
    {'name': 'Alpha', 'type': 'A2527', 'faction': 'One', 'player': 'Serge', 'x': 0, 'y': 0},
    {'name': 'Beta', 'type': 'A2527', 'faction': 'One', 'player': 'Serge', 'x': 10, 'y': 0},
    {'name': 'Bravo', 'type': 'A2527', 'faction': 'Two', 'player': 'Ilya', 'x': 100, 'y': 100},
]


class TestReminding(TestCase):
    """Who gets poked before a deadline, and how the journal keeps it to once each."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.speaker = Loudspeaker()
        self.admin = AdminService(self.root, announcer=Announcer([self.speaker]))
        self.game = GameService(self.root, announcer=Announcer([self.speaker]))
        self.admin.create_game(GAME, SHIPS, 'generic')
        self._processes_at(self._hour_in(5))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    @staticmethod
    def _hour_in(hours: int) -> int:
        return (server_now() + timedelta(hours=hours)).hour

    def _processes_at(self, *hours: int, announce: bool = True) -> None:
        self.admin.save_settings(GAME, GameSettings(on_all_ready=False, process_hours=list(hours),
                                                    announce=announce))

    def _wants(self, *rows: tuple) -> None:
        """Who wants reminding, written the way a director sets it today: into the file."""
        with open(os.path.join(self.root, PLAYERS_FILE_NAME), 'w') as f:
            for name, discord_id, hours_before in rows:
                f.write(json.dumps({'name': name, 'discord_id': discord_id,
                                    'remind_hours_before': hours_before}) + '\n')

    def _wants_daily(self, *rows: tuple) -> None:
        """The other setting: an hour of their own day, and the clock it is on."""
        with open(os.path.join(self.root, PLAYERS_FILE_NAME), 'w') as f:
            for name, discord_id, hour, zone in rows:
                f.write(json.dumps({'name': name, 'discord_id': discord_id,
                                    'remind_daily_hour': hour, 'timezone': zone}) + '\n')

    def _long_enough(self) -> int:
        """A lead time that reaches this game's next deadline, whenever the suite is run."""
        due = next_occurrence(self.admin.settings(GAME).process_hours, server_now())
        return int((due - server_now()).total_seconds() / 3600) + 1

    def test_nobody_is_reminded_without_asking(self):
        self.assertEqual([], self.admin.remind_due())
        self.assertEqual([], self.speaker.heard)

    def test_a_lead_time_short_of_the_deadline_waits(self):
        self._wants(('Serge', '4242', 1))
        self.assertEqual([], self.admin.remind_due())
        self.assertEqual([], self.speaker.heard)

    def test_a_lead_time_that_reaches_the_deadline_pokes(self):
        self._wants(('Serge', '4242', self._long_enough()))
        self.assertEqual([f"{GAME}: deadline reminder to Serge"], self.admin.remind_due())
        self.assertEqual(1, len(self.speaker.heard))
        self.assertIn('<@4242>', self.speaker.heard[0])
        self.assertIn('Deep Space', self.speaker.heard[0])

    def test_an_id_without_a_lead_time_is_not_opted_in(self):
        self._wants(('Serge', '4242', 0))
        self.assertEqual([], self.admin.remind_due())

    def test_a_lead_time_without_an_id_has_nowhere_to_go(self):
        self._wants(('Serge', '', self._long_enough()))
        self.assertEqual([], self.admin.remind_due())

    def test_a_player_is_poked_once_for_a_round(self):
        self._wants(('Serge', '4242', self._long_enough()))
        self.admin.remind_due()
        self.speaker.heard.clear()
        self.assertEqual([], self.admin.remind_due())
        self.assertEqual([], self.speaker.heard)

    def test_a_shorter_lead_time_is_not_silenced_by_a_longer_one(self):
        """The journal records who was poked, so the next one along still gets theirs."""
        long = self._long_enough()
        self._wants(('Serge', '1111', long))
        self.admin.remind_due()
        self.speaker.heard.clear()
        self._wants(('Serge', '1111', long), ('Ilya', '2222', long))
        self.assertEqual([f"{GAME}: deadline reminder to Ilya"], self.admin.remind_due())
        self.assertIn('<@2222>', self.speaker.heard[0])
        self.assertNotIn('<@1111>', self.speaker.heard[0])

    def test_orders_in_for_the_whole_fleet_is_nothing_to_remind(self):
        self._wants(('Serge', '4242', self._long_enough()))
        for ship in ('Alpha', 'Beta'):
            self.game.save_commands(GAME, ship, ['turn 10'])
        self.assertEqual([], self.admin.remind_due())

    def test_one_ship_of_a_fleet_short_still_owes_orders(self):
        self._wants(('Serge', '4242', self._long_enough()))
        self.game.save_commands(GAME, 'Alpha', ['turn 10'])
        self.assertEqual([f"{GAME}: deadline reminder to Serge"], self.admin.remind_due())

    def test_a_game_told_not_to_announce_stays_quiet(self):
        self._wants(('Serge', '4242', self._long_enough()))
        self._processes_at(self._hour_in(5), announce=False)
        self.assertEqual([], self.admin.remind_due())
        self.assertEqual([], self.speaker.heard)

    def test_a_game_that_never_processes_has_no_deadline_to_be_early_for(self):
        self._wants(('Serge', '4242', 24))
        self._processes_at()
        self.assertEqual([], self.admin.remind_due())

    def test_a_daily_hour_already_past_on_their_clock_pokes(self):
        # Midnight has gone by whatever zone they are in, so this fires wherever the suite runs.
        self._wants_daily(('Serge', '4242', 0, 'Europe/Amsterdam'))
        self.assertEqual([f"{GAME}: daily reminder to Serge"], self.admin.remind_due())
        self.assertIn('<@4242>', self.speaker.heard[0])

    def test_a_daily_poke_does_not_repeat_the_same_day(self):
        self._wants_daily(('Serge', '4242', 0, 'Europe/Amsterdam'))
        self.admin.remind_due()
        self.speaker.heard.clear()
        self.assertEqual([], self.admin.remind_due())
        self.assertEqual([], self.speaker.heard)

    def test_a_daily_setting_needs_a_zone_to_be_an_hour_of_anything(self):
        self._wants_daily(('Serge', '4242', 0, ''))
        self.assertEqual([], self.admin.remind_due())

    def test_the_two_settings_are_independent(self):
        """One person on a daily hour, another on a lead time, both owing, both reached."""
        with open(os.path.join(self.root, PLAYERS_FILE_NAME), 'w') as f:
            f.write(json.dumps({'name': 'Serge', 'discord_id': '1111',
                                'remind_daily_hour': 0, 'timezone': 'Europe/Amsterdam'}) + '\n')
            f.write(json.dumps({'name': 'Ilya', 'discord_id': '2222',
                                'remind_hours_before': self._long_enough()}) + '\n')
        self.assertEqual([f"{GAME}: deadline reminder to Ilya",
                          f"{GAME}: daily reminder to Serge"], self.admin.remind_due())
        self.assertEqual(2, len(self.speaker.heard))

    def test_both_settings_on_one_person_are_two_pokes(self):
        """Asking for both is asking for both. The journal tells them apart by trigger."""
        with open(os.path.join(self.root, PLAYERS_FILE_NAME), 'w') as f:
            f.write(json.dumps({'name': 'Serge', 'discord_id': '1111',
                                'remind_hours_before': self._long_enough(),
                                'remind_daily_hour': 0,
                                'timezone': 'Europe/Amsterdam'}) + '\n')
        self.assertEqual([f"{GAME}: deadline reminder to Serge",
                          f"{GAME}: daily reminder to Serge"], self.admin.remind_due())
        self.assertEqual(['deadline', 'daily'],
                         [e.detail['trigger'] for e in self.admin.journal(GAME)
                          if e.event == 'reminded'][::-1])

    def test_a_reminder_that_went_nowhere_is_not_recorded_as_sent(self):
        """A dead channel must leave them owed a poke, not marked as having had one."""
        broken = Loudspeaker(working=False)
        admin = AdminService(self.root, announcer=Announcer([broken]))
        self._wants(('Serge', '4242', self._long_enough()))
        self.assertEqual([f"{GAME}: deadline reminder to Serge went nowhere"], admin.remind_due())
        self.assertEqual([], [e for e in admin.journal(GAME) if e.event == 'reminded'])
        # And the next pass, on a channel that works, still reaches them.
        self.assertEqual([f"{GAME}: deadline reminder to Serge"], self.admin.remind_due())

    def test_a_new_round_pokes_again(self):
        long = self._long_enough()
        self._wants(('Serge', '1111', long), ('Ilya', '2222', long))
        self.admin.remind_due()
        for ship in ('Alpha', 'Beta', 'Bravo'):
            self.game.save_commands(GAME, ship, ['turn 10'])
        self.admin.process_turn(GAME)
        self.speaker.heard.clear()
        self.assertEqual([f"{GAME}: deadline reminder to Ilya, Serge"], self.admin.remind_due())