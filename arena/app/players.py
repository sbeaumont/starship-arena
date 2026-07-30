"""Who can log in. One token per person, and the name is their identity in every game.

See docs/data.md for the file format and what a token is."""

import logging
import os
import secrets
from dataclasses import dataclass

from arena.cfg import PLAYERS_FILE_NAME

logger = logging.getLogger('starship-arena.players')

# A play-by-mail game runs for months, so the cookie outlives any session.
LOGIN_COOKIE = 'arena_login'
LOGIN_COOKIE_MAX_AGE = 60 * 60 * 24 * 365
TOKEN_BYTES = 16
DIRECTOR = 'director'
COLUMNS = ('Name', 'Token', 'Role')


@dataclass
class Player:
    name: str
    token: str
    role: str = ''

    @property
    def is_director(self) -> bool:
        return self.role == DIRECTOR


class PlayerRegistry:
    """The people who can log in, read from and written to players.txt."""

    def __init__(self, data_root: str):
        self.path = os.path.join(str(data_root), PLAYERS_FILE_NAME)

    def all(self) -> list[Player]:
        if not os.path.exists(self.path):
            return []
        players = []
        with open(self.path) as f:
            for line in f:
                fields = line.split()
                if not fields or fields[0].startswith('#') or fields[0] == COLUMNS[0]:
                    continue
                players.append(Player(name=fields[0], token=fields[1],
                                      role=fields[2] if len(fields) > 2 else ''))
        return players

    def by_token(self, token: str) -> Player | None:
        """Who holds this token, or None. Constant-time compare: it is a secret."""
        if not token:
            return None
        for p in self.all():
            if secrets.compare_digest(p.token, token):
                return p
        return None

    def by_name(self, name: str) -> Player | None:
        return next((p for p in self.all() if p.name == name), None)

    def issue(self, name: str, role: str = '') -> Player:
        """A fresh token, replacing any they had. Rotating a leaked link is the same call."""
        players = [p for p in self.all() if p.name != name]
        issued = Player(name=name, token=secrets.token_urlsafe(TOKEN_BYTES), role=role)
        players.append(issued)
        self._save(players)
        logger.info(f"Issued a login token for {name}{' (director)' if issued.is_director else ''}")
        return issued

    def revoke(self, name: str) -> None:
        self._save([p for p in self.all() if p.name != name])

    def _save(self, players: list[Player]) -> None:
        widths = [max(len(c), *(len(getattr(p, c.lower())) for p in players)) for c in COLUMNS] \
            if players else [len(c) for c in COLUMNS]
        lines = ['  '.join(c.ljust(w) for c, w in zip(COLUMNS, widths)).rstrip()]
        for p in sorted(players, key=lambda x: x.name):
            fields = (p.name, p.token, p.role)
            lines.append('  '.join(v.ljust(w) for v, w in zip(fields, widths)).rstrip())
        with open(self.path, 'w') as f:
            f.write('\n'.join(lines) + '\n')