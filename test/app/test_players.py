import os
import shutil
import tempfile
from unittest import TestCase

from arena.app.players import PlayerRegistry, DIRECTOR


class TestPlayerRegistry(TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.registry = PlayerRegistry(self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, content: str) -> None:
        with open(os.path.join(self.root, 'players.jsonl'), 'w') as f:
            f.write(content)

    def test_no_file_yet(self):
        self.assertEqual([], self.registry.all())
        self.assertIsNone(self.registry.by_token('anything'))

    def test_issue_and_resolve(self):
        issued = self.registry.issue('Menno')
        self.assertEqual('Menno', self.registry.by_token(issued.token).name)
        self.assertFalse(issued.is_director)

    def test_a_director_is_marked(self):
        self.registry.issue('Serge', role=DIRECTOR)
        self.assertTrue(self.registry.by_name('Serge').is_director)

    def test_issuing_again_replaces_the_token(self):
        first = self.registry.issue('Menno')
        second = self.registry.issue('Menno')
        self.assertNotEqual(first.token, second.token)
        self.assertIsNone(self.registry.by_token(first.token))
        self.assertEqual('Menno', self.registry.by_token(second.token).name)
        self.assertEqual(1, len(self.registry.all()))

    def test_remove(self):
        issued = self.registry.issue('Menno')
        self.registry.remove('Menno')
        self.assertIsNone(self.registry.by_token(issued.token))
        self.assertEqual([], self.registry.all())

    def test_survives_a_round_trip_through_the_file(self):
        self.registry.issue('Serge', role=DIRECTOR)
        self.registry.issue('Menno')
        reread = PlayerRegistry(self.root).all()
        self.assertEqual(['Menno', 'Serge'], [p.name for p in reread])
        self.assertEqual([False, True], [p.is_director for p in reread])

    def test_ignores_comments_and_blank_lines(self):
        self.write('# a note\n\n{"name": "Menno", "token": "abc123"}\n')
        self.assertEqual(['Menno'], [p.name for p in self.registry.all()])
        self.assertEqual('Menno', self.registry.by_token('abc123').name)

    def test_only_the_name_is_required(self):
        self.write('{"name": "Menno"}\n')
        menno = self.registry.by_name('Menno')
        self.assertEqual('', menno.token)
        self.assertFalse(menno.is_director)
        self.assertTrue(menno.active)

    def test_a_line_that_will_not_parse_names_itself(self):
        self.write('{"name": "Menno"}\nnot json\n')
        with self.assertRaises(ValueError) as raised:
            self.registry.all()
        self.assertIn('line 2', str(raised.exception))

    def test_deactivating_keeps_the_name_and_closes_the_door(self):
        issued = self.registry.issue('Menno')
        self.registry.set_active('Menno', False)
        self.assertIsNone(self.registry.by_token(issued.token))
        self.assertFalse(self.registry.by_name('Menno').active)

    def test_reactivating_gives_the_same_token_back(self):
        issued = self.registry.issue('Menno')
        self.registry.set_active('Menno', False)
        self.registry.set_active('Menno', True)
        self.assertEqual('Menno', self.registry.by_token(issued.token).name)

    def test_a_new_link_does_not_reactivate(self):
        self.registry.issue('Menno')
        self.registry.set_active('Menno', False)
        again = self.registry.issue('Menno')
        self.assertIsNone(self.registry.by_token(again.token))

    def test_deactivating_someone_with_no_link_gives_them_a_row(self):
        # The names that clutter the console are old ones from game history, which have no login
        # to hang an Active flag off. They get a row of their own so they can be put aside.
        self.registry.set_active('Menno', False)
        menno = self.registry.by_name('Menno')
        self.assertFalse(menno.active)
        self.assertEqual('', menno.token)

    def test_a_deactivated_stranger_survives_the_file(self):
        self.registry.set_active('Menno', False)
        self.assertEqual([False], [p.active for p in PlayerRegistry(self.root).all()])

    def test_both_reminders_are_off_until_they_are_asked_for(self):
        self.write('{"name": "Menno"}\n')
        menno = self.registry.by_name('Menno')
        self.assertEqual('', menno.discord_id)
        self.assertEqual(0, menno.remind_hours_before)
        self.assertFalse(menno.wants_deadline_reminder)
        self.assertFalse(menno.wants_daily_reminder)

    def test_a_deadline_reminder_survives_the_file(self):
        self.write('{"name": "Menno", "discord_id": "4242", "remind_hours_before": 6}\n')
        menno = PlayerRegistry(self.root).by_name('Menno')
        self.assertTrue(menno.wants_deadline_reminder)
        self.assertFalse(menno.wants_daily_reminder)
        self.assertEqual('4242', menno.discord_id)
        self.assertEqual(6, menno.remind_hours_before)

    def test_a_daily_reminder_survives_the_file(self):
        self.write('{"name": "Menno", "discord_id": "4242", "remind_daily_hour": 8,'
                   ' "timezone": "Europe/Amsterdam"}\n')
        menno = PlayerRegistry(self.root).by_name('Menno')
        self.assertTrue(menno.wants_daily_reminder)
        self.assertFalse(menno.wants_deadline_reminder)
        self.assertEqual(8, menno.remind_daily_hour)

    def test_midnight_is_an_hour_like_any_other(self):
        """Nought is a real answer here, which is why absence is what says nobody asked."""
        self.write('{"name": "Menno", "discord_id": "4242", "remind_daily_hour": 0,'
                   ' "timezone": "Europe/Amsterdam"}\n')
        self.assertTrue(PlayerRegistry(self.root).by_name('Menno').wants_daily_reminder)

    def test_the_two_reminders_are_asked_for_separately(self):
        self.write('{"name": "Menno", "discord_id": "4242", "remind_daily_hour": 8}\n')
        # An hour with no clock under it is not an hour of anything.
        self.assertFalse(self.registry.by_name('Menno').wants_daily_reminder)

    def test_a_new_link_keeps_the_reminders(self):
        self.write('{"name": "Menno", "discord_id": "4242", "remind_hours_before": 6,'
                   ' "remind_daily_hour": 8, "timezone": "Europe/Amsterdam"}\n')
        self.registry.issue('Menno')
        menno = PlayerRegistry(self.root).by_name('Menno')
        self.assertTrue(menno.wants_deadline_reminder)
        self.assertTrue(menno.wants_daily_reminder)