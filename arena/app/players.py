"""Who can log in. One token per person, and the name is their identity in every game.

See docs/data.md for the file format and what a token is."""

import logging
import os
import re
import secrets
from dataclasses import dataclass

from arena.cfg import PLAYERS_FILE_NAME

logger = logging.getLogger('starship-arena.players')

# A play-by-mail game runs for months, so the cookie outlives any session.
LOGIN_COOKIE = 'arena_login'
LOGIN_COOKIE_MAX_AGE = 60 * 60 * 24 * 365
TOKEN_BYTES = 16
DIRECTOR = 'director'
PLAYER = 'player'
COLUMNS = ('Name', 'Token', 'Role', 'Active')


def as_stored(name: str) -> str:
    """A name is a column in a whitespace-split file and part of a filename, so it holds no
    spaces. See docs/data.md."""
    return re.sub(r'\s+', '_', name.strip())


@dataclass
class Player:
    name: str
    token: str
    role: str = PLAYER
    active: bool = True

    @property
    def is_director(self) -> bool:
        return self.role == DIRECTOR


class PlayerRegistry:
    """The people who can log in, read from and written to players.txt."""

    def __init__(self, data_root: str):
        self.path = os.path.join(str(data_root), PLAYERS_FILE_NAME)

    def all(self) -> list[Player]:
        """Columns are read by position, so every one of them is written out: see docs/data.md."""
        if not os.path.exists(self.path):
            return []
        players = []
        with open(self.path) as f:
            for line in f:
                fields = line.split()
                if not fields or fields[0].startswith('#') or fields[0] == COLUMNS[0]:
                    continue
                players.append(Player(name=fields[0], token=fields[1],
                                      role=fields[2] if len(fields) > 2 else PLAYER,
                                      active=len(fields) < 4 or fields[3] != 'no'))
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
        return next((p for p in self.all() if p.name == as_stored(name)), None)

    def issue(self, name: str, role: str = PLAYER) -> Player:
        """A fresh token, replacing any they had. Rotating a leaked link is the same call."""
        name = as_stored(name)
        had = self.by_name(name)
        players = [p for p in self.all() if p.name != name]
        issued = Player(name=name, token=secrets.token_urlsafe(TOKEN_BYTES), role=role,
                        active=had.active if had else True)
        players.append(issued)
        self._save(players)
        logger.info(f"Issued a login token for {name}{' (director)' if issued.is_director else ''}")
        return issued

    def revoke(self, name: str) -> None:
        self._save([p for p in self.all() if p.name != name])

    def set_active(self, name: str, active: bool) -> None:
        players = self.all()
        theirs = next((p for p in players if p.name == name), None)
        if theirs is None:
            raise ValueError(f"Nobody called '{name}' is registered.")
        theirs.active = active
        self._save(players)
        logger.info(f"{name} is now {'active' if active else 'deactivated'}")

    @staticmethod
    def _fields(p: Player) -> tuple:
        return p.name, p.token, p.role, 'yes' if p.active else 'no'

    def _save(self, players: list[Player]) -> None:
        rows = [COLUMNS] + [self._fields(p) for p in sorted(players, key=lambda x: x.name)]
        widths = [max(len(row[i]) for row in rows) for i in range(len(COLUMNS))]
        lines = ['  '.join(v.ljust(w) for v, w in zip(row, widths)).rstrip() for row in rows]
        with open(self.path, 'w') as f:
            f.write('\n'.join(lines) + '\n')