"""Who put themselves down for a game that has not started yet."""

import json
import os
import re
from dataclasses import dataclass, field

from arena.cfg import REGISTRATION_FILE_NAME

# A ship's name ends up in a command file's name, so it has to survive being part of a path.
SHIP_NAME = re.compile(r'[A-Za-z][A-Za-z0-9_-]*$')


@dataclass
class Registration:
    player: str
    names: list[str] = field(default_factory=list)
    faction: str = ''   # where the director put them; empty means the deal decides

    @property
    def ships(self) -> int:
        return len(self.names)


class RegistrationFile:
    """One JSON object per line, in the game's own directory."""

    def __init__(self, game_dir: str):
        self.path = os.path.join(str(game_dir), REGISTRATION_FILE_NAME)

    def all(self) -> list[Registration]:
        if not os.path.exists(self.path):
            return []
        entries = []
        with open(self.path) as f:
            for number, line in enumerate(f, start=1):
                if not line.strip() or line.lstrip().startswith('#'):
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(f"{self.path} line {number}: {e}") from e
                entries.append(Registration(player=record['player'], names=record['names'],
                                            faction=record.get('faction', '')))
        return entries

    def of(self, player: str) -> Registration | None:
        return next((e for e in self.all() if e.player == player), None)

    def put(self, player: str, names: list[str], max_ships: int) -> Registration:
        """Register, or change what you registered for. One ship per name."""
        if not 1 <= len(names) <= max_ships:
            raise ValueError(f"Name between 1 and {max_ships} ships.")
        malformed = [n for n in names if not SHIP_NAME.match(n)]
        if malformed:
            raise ValueError("A ship's name starts with a letter and holds only letters, numbers, "
                             f"dashes and underscores: {', '.join(malformed)}")
        if len(set(names)) != len(names):
            raise ValueError("Two of your ships have the same name.")
        others = self.all()
        taken = {n for e in others if e.player != player for n in e.names}
        clashes = [n for n in names if n in taken]
        if clashes:
            raise ValueError(f"Already taken by somebody else: {', '.join(clashes)}.")
        mine = Registration(player=player, names=names,
                            faction=self.of(player).faction if self.of(player) else '')
        self._save([e for e in others if e.player != player] + [mine])
        return mine

    def remove(self, player: str) -> None:
        self._save([e for e in self.all() if e.player != player])

    def assign(self, factions: dict[str, str]) -> None:
        """Where the director has put people so far. Anyone absent goes back into the pool."""
        entries = self.all()
        for entry in entries:
            entry.faction = factions.get(entry.player, '')
        self._save(entries)

    def _save(self, entries: list[Registration]) -> None:
        with open(self.path, 'w') as f:
            for e in sorted(entries, key=lambda x: x.player):
                record = {'player': e.player, 'names': e.names}
                if e.faction:
                    record['faction'] = e.faction
                f.write(json.dumps(record) + '\n')