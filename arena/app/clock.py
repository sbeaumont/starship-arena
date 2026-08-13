"""What time it is on the server. See docs/adr/0027-the-server-keeps-one-timezone.md.

A game's hours are the server's. A player's own reminder is the one thing kept on their clock, as
a zone name rather than an offset, so daylight saving moves it the way their morning moves.
See docs/adr/0037-players-are-reminded-before-a-deadline.md."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

if datetime.now().astimezone().tzname() is None:
    raise RuntimeError("This host reports no timezone of its own, so it cannot say what time it "
                       "keeps. Give it one before running a game on it.")


def server_now() -> datetime:
    """Now, in the host's zone. Shifting to a reader's clock is an interface's business."""
    return datetime.now().astimezone()


def zone_name() -> str:
    """What to call the server's zone, as the host abbreviates it: 'CEST', 'UTC'."""
    return server_now().tzname()


def their_hour_today(hour: int, zone: str, now: datetime) -> datetime:
    """A reader's own hour of today, as a moment the server can compare against.

    Read against their zone's rules on the day itself, which is what keeps a chosen hour the same
    hour of the same morning after a daylight saving shift. An unknown zone raises."""
    theirs = now.astimezone(ZoneInfo(zone))
    return datetime.combine(theirs.date(), time(hour=hour), tzinfo=theirs.tzinfo)


def next_occurrence(hours: list[int], after: datetime) -> datetime | None:
    """The next moment the server's clock reads one of these hours. None when there are none."""
    for day in (after.date(), after.date() + timedelta(days=1)):
        for hour in sorted(hours):
            moment = datetime.combine(day, time(hour=hour)).astimezone()
            if moment > after:
                return moment
    return None