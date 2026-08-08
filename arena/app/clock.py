"""What time it is on the server. See docs/adr/0027-the-server-keeps-one-timezone.md."""

from datetime import datetime, time, timedelta

if datetime.now().astimezone().tzname() is None:
    raise RuntimeError("This host reports no timezone of its own, so it cannot say what time it "
                       "keeps. Give it one before running a game on it.")


def server_now() -> datetime:
    """Now, in the host's zone. Shifting to a reader's clock is an interface's business."""
    return datetime.now().astimezone()


def zone_name() -> str:
    """What to call the server's zone, as the host abbreviates it: 'CEST', 'UTC'."""
    return server_now().tzname()


def next_occurrence(hours: list[int], after: datetime) -> datetime | None:
    """The next moment the server's clock reads one of these hours. None when there are none."""
    for day in (after.date(), after.date() + timedelta(days=1)):
        for hour in sorted(hours):
            moment = datetime.combine(day, time(hour=hour)).astimezone()
            if moment > after:
                return moment
    return None