"""
Who may log in.

A player's name is their identity across every game, so the registry lives at the data root
rather than inside a game directory. A token is a long random string that stands for the person
who holds it: it goes out in a link, comes back in a cookie, and is what an interface trades for
an identity. Kept in plain text so a link can be sent again.

The file is the same shape as ships.txt - a header line naming the columns, whitespace separated,
lines starting with # ignored:

    Name   Token                 Role
    Serge  k3Jd9x_2mQpLzR7t      director
    Menno  8fQnT1wVbY4hLs0e
"""

import logging
import os
import secrets
from dataclasses import dataclass

from arena.cfg import PLAYERS_FILE_NAME

logger = logging.getLogger('starship-arena.players')

LOGIN_COOKIE = 'arena_login'
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
        """Who holds this token, or None. Compared in constant time, since it is a secret."""
        if not token:
            return None
        for p in self.all():
            if secrets.compare_digest(p.token, token):
                return p
        return None

    def by_name(self, name: str) -> Player | None:
        return next((p for p in self.all() if p.name == name), None)

    def issue(self, name: str, role: str = '') -> Player:
        """Give this player a fresh token, replacing any they had, and return them.

        Rotating is the same operation as issuing: a link that leaked is replaced by asking for
        another one."""
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