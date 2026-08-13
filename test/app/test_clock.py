from datetime import datetime
from unittest import TestCase
from zoneinfo import ZoneInfo

from arena.app.clock import their_hour_today

AMSTERDAM = 'Europe/Amsterdam'
UTC = ZoneInfo('UTC')


class TestTheirHourToday(TestCase):
    """A player's own hour, read on their clock and answered as a moment the server can use."""

    def test_an_hour_of_their_day_is_a_moment_on_the_server_clock(self):
        now = datetime(2026, 8, 13, 9, 0, tzinfo=UTC)
        self.assertEqual(datetime(2026, 8, 13, 6, 0, tzinfo=UTC),
                         their_hour_today(8, AMSTERDAM, now).astimezone(UTC))

    def test_their_day_is_the_one_they_are_in_not_the_server_s(self):
        # 23:30 UTC is already the 14th in Amsterdam, so their 08:00 is the 14th's.
        now = datetime(2026, 8, 13, 23, 30, tzinfo=UTC)
        self.assertEqual(datetime(2026, 8, 14, 6, 0, tzinfo=UTC),
                         their_hour_today(8, AMSTERDAM, now).astimezone(UTC))

    def test_the_same_morning_either_side_of_a_daylight_saving_shift(self):
        """Why the zone is stored by name. 08:00 stays 08:00 to them; the offset does the moving."""
        summer = their_hour_today(8, AMSTERDAM, datetime(2026, 8, 13, 9, tzinfo=UTC))
        winter = their_hour_today(8, AMSTERDAM, datetime(2026, 12, 13, 9, tzinfo=UTC))
        self.assertEqual(8, summer.hour)
        self.assertEqual(8, winter.hour)
        self.assertEqual(6, summer.astimezone(UTC).hour)
        self.assertEqual(7, winter.astimezone(UTC).hour)

    def test_a_zone_nobody_keeps_says_so(self):
        with self.assertRaises(Exception):
            their_hour_today(8, 'Mars/Olympus', datetime(2026, 8, 13, 9, tzinfo=UTC))