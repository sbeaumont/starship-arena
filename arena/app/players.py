"""Who can log in. One token per person, and the name is their identity in every game.

See docs/data.md for the file format and what a token is."""

import json
import logging
import os
import secrets
from dataclasses import dataclass

from arena.cfg import PLAYERS_FILE_NAME

logger = logging.getLogger('starship-arena.players')

# A play-by-mail game runs for months, so the cookie outlives any session.
LOGIN_COOKIE = 'arena_login'
LOGIN_COOKIE_MAX_AGE = 60 * 60 * 24 * 365
# A browser keeps a Secure cookie over https, and over localhost, and nowhere else. Trying the
# UI on a phone means a plain address on the network, where the cookie would be dropped and
# every call would come back 401, so the dev runner turns this off. Nothing else ever does.
LOGIN_COOKIE_SECURE = os.environ.get('ARENA_INSECURE_COOKIES') != '1'
TOKEN_BYTES = 16
DIRECTOR = 'director'
PLAYER = 'player'

# A name becomes the directory name of that person's solo game, so it may not walk out of one.
# A single dot stays allowed, because "St. Nicolaas" is a name somebody will want.
FORBIDDEN_IN_A_NAME = ('..', '/', '\\')


def check_name(name: str) -> None:
    if not (name and name.strip()):
        raise ValueError("A name cannot be empty.")
    if any(bad in name for bad in FORBIDDEN_IN_A_NAME):
        raise ValueError(f"'{name}' cannot be a name: no '..', no slashes.")


@dataclass
class Player:
    name: str
    token: str = ''
    role: str = PLAYER
    active: bool = True
    discord_id: str = ''
    remind_hours_before: int = 0
    # An hour of their day, 0 to 23. None is nobody asking; midnight is an hour like any other.
    remind_daily_hour: int | None = None
    timezone: str = ''

    @property
    def is_director(self) -> bool:
        return self.role == DIRECTOR

    @property
    def wants_deadline_reminder(self) -> bool:
        """Somewhere to reach them, and how long before a game's deadline they want it."""
        return bool(self.discord_id) and self.remind_hours_before > 0

    @property
    def wants_daily_reminder(self) -> bool:
        """Somewhere to reach them, an hour of their day, and the clock that hour is on."""
        return bool(self.discord_id and self.timezone) and self.remind_daily_hour is not None


class PlayerRegistry:
    """The people who can log in, read from and written to players.jsonl."""

    def __init__(self, data_root: str):
        self.path = os.path.join(str(data_root), PLAYERS_FILE_NAME)

    def all(self) -> list[Player]:
        """One JSON object per line. Only `name` is required: see docs/data.md."""
        if not os.path.exists(self.path):
            return []
        players = []
        with open(self.path) as f:
            for number, line in enumerate(f, start=1):
                if not line.strip() or line.lstrip().startswith('#'):
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(f"{self.path} line {number}: {e}") from e
                players.append(Player(name=record['name'], token=record.get('token', ''),
                                      role=record.get('role', PLAYER),
                                      active=record.get('active', True),
                                      discord_id=record.get('discord_id', ''),
                                      remind_hours_before=record.get('remind_hours_before', 0),
                                      remind_daily_hour=record.get('remind_daily_hour'),
                                      timezone=record.get('timezone', '')))
        return players

    def by_token(self, token: str) -> Player | None:
        """Who holds this token, or None. Constant-time compare: it is a secret."""
        if not token:
            return None
        for p in self.all():
            if p.active and secrets.compare_digest(p.token, token):
                return p
        return None

    def by_name(self, name: str) -> Player | None:
        return next((p for p in self.all() if p.name == name), None)

    def issue(self, name: str, role: str = PLAYER) -> Player:
        """A fresh token, replacing any they had. Rotating a leaked link is the same call.

        Everything else on the row survives it, so rotating a link does not cost somebody the
        settings they chose."""
        check_name(name)
        players = self.all()
        issued = next((p for p in players if p.name == name), None)
        if issued is None:
            issued = Player(name=name)
            players.append(issued)
        issued.token = secrets.token_urlsafe(TOKEN_BYTES)
        issued.role = role
        self._save(players)
        logger.info(f"Issued a login token for {name}{' (director)' if issued.is_director else ''}")
        return issued

    def remove(self, name: str) -> None:
        """Take the row away for good, freeing the name for anyone to claim."""
        self._save([p for p in self.all() if p.name != name])
        logger.info(f"Removed {name}")

    def remove_link(self, name: str) -> None:
        """Take the token away and keep the person. Nothing they hold opens a door."""
        players = self.all()
        theirs = next((p for p in players if p.name == name), None)
        if theirs is None:
            raise ValueError(f"Nobody called '{name}' is registered.")
        theirs.token = ''
        self._save(players)
        logger.info(f"Took away {name}'s link")

    def set_reminders(self, name: str, discord_id: str, hours_before: int,
                      daily_hour: int | None, timezone: str) -> Player:
        """What somebody asked to be reminded by. The rest of their row is left alone."""
        players = self.all()
        theirs = next((p for p in players if p.name == name), None)
        if theirs is None:
            raise ValueError(f"Nobody called '{name}' is registered.")
        theirs.discord_id = discord_id
        theirs.remind_hours_before = hours_before
        theirs.remind_daily_hour = daily_hour
        theirs.timezone = timezone
        self._save(players)
        logger.info(f"{name} set their reminders")
        return theirs

    def set_active(self, name: str, active: bool) -> None:
        """Someone who has never held a link gets a row here, so any name can be put aside."""
        players = self.all()
        theirs = next((p for p in players if p.name == name), None)
        if theirs is None:
            theirs = Player(name=name)
            players.append(theirs)
        theirs.active = active
        self._save(players)
        logger.info(f"{name} is now {'active' if active else 'deactivated'}")

    @staticmethod
    def _record(p: Player) -> dict:
        """Defaults are left out, so a line says only what is true of this person."""
        record = {'name': p.name}
        if p.token:
            record['token'] = p.token
        if p.role != PLAYER:
            record['role'] = p.role
        if not p.active:
            record['active'] = False
        if p.discord_id:
            record['discord_id'] = p.discord_id
        if p.remind_hours_before:
            record['remind_hours_before'] = p.remind_hours_before
        if p.remind_daily_hour is not None:
            record['remind_daily_hour'] = p.remind_daily_hour
        if p.timezone:
            record['timezone'] = p.timezone
        return record

    def _save(self, players: list[Player]) -> None:
        with open(self.path, 'w') as f:
            for p in sorted(players, key=lambda x: x.name):
                f.write(json.dumps(self._record(p)) + '\n')