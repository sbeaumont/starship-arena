"""
Abstraction of a directory of a specific game of Space Arena.

- Hides all the specific information about structure and file names.
- Performs specific file operations on the directory.
"""

import fnmatch
import json
import re
import shutil
import pickle
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from abc import ABC

from arena.cfg import *
from arena.errors import UnreadableWorld
from arena.engine.world import World
import logging

logger = logging.getLogger('starship-arena.gamedirectory')


class _Stubbing(pickle.Unpickler):
    """Reads a world by standing in for whatever the code has dropped, and counting it.

    Diagnosis only: what it builds has holes where the stand-ins are, and the regenerate
    invariant is why no caller may keep it. See docs/architecture.md."""

    def __init__(self, f):
        super().__init__(f)
        self.absent = {}

    def find_class(self, module: str, name: str):
        try:
            return super().find_class(module, name)
        except (AttributeError, ImportError):
            self.absent[f"{module}.{name}"] = self.absent.get(f"{module}.{name}", 0) + 1
            return type(name, (), {'__init__': lambda s, *a, **kw: None,
                                   '__setstate__': lambda s, state: None})


class GamesIn(str, Enum):
    """One of the roots a game can be in, named after it."""
    Playing = GAMES_DIR_NAME
    Archived = ARCHIVE_DIR_NAME
    Registering = REGISTERING_DIR_NAME
    Solo = SOLO_DIR_NAME

    def __str__(self):
        return self.value

    @property
    def planned(self) -> bool:
        """Whether a round is being planned in here. Nothing is owed for the other two."""
        return self in (GamesIn.Playing, GamesIn.Solo)


@dataclass(frozen=True)
class GamesRoot:
    """A data root, and the four places a game directory can be in it."""

    root: Path

    def path(self, where: GamesIn) -> Path:
        return self.root / where.value

    @property
    def games(self) -> Path:
        return self.path(GamesIn.Playing)

    @property
    def archived(self) -> Path:
        return self.path(GamesIn.Archived)

    @property
    def registering(self) -> Path:
        return self.path(GamesIn.Registering)

    @property
    def solo(self) -> Path:
        return self.path(GamesIn.Solo)

    def directory_in(self, where: GamesIn, game: str) -> 'GameDirectory':
        return GameDirectory(str(self.path(where)), game, where)

    def directory(self, game: str) -> 'GameDirectory':
        """A playable game, wherever it is playable from.

        There is nothing to disambiguate: a shared game may not be named what a solo game is or
        could be called. Resolving it here is what lets one set of operations serve both, so a
        solo game is planned, ordered and processed through exactly the calls a shared game is.
        See docs/adr/0030-solo-games-live-in-their-own-root.md."""
        where = GamesIn.Solo if (self.solo / game).is_dir() else GamesIn.Playing
        return self.directory_in(where, game)

    def directories_in(self, where: GamesIn) -> list['GameDirectory']:
        """Every game in one root, in name order. Empty while the root has never been made."""
        root = self.path(where)
        if not root.exists():
            return []
        return [self.directory_in(where, d.name)
                for d in sorted(p for p in root.iterdir() if p.is_dir())]

    def playable(self) -> list['GameDirectory']:
        """Shared games and everybody's own, which are the two a round is planned in."""
        return [gd for where in GamesIn if where.planned
                for gd in self.directories_in(where)]


class GameDirectory(object):
    def __init__(self, data_root: str, game_name: str, where: GamesIn = GamesIn.Playing):
        self._dir = os.path.join(data_root, game_name)
        self.game_name = game_name
        self.where = where

    @property
    def planned(self) -> bool:
        """Whether a round is being planned here, which is a fact about where it is kept."""
        return self.where.planned

    @property
    def has_been_setup(self):
        return self.last_round_number >= 0

    # ---------------------------------------------------------------------- QUERIES - Filenames

    @property
    def exists(self) -> bool:
        return os.path.exists(self._dir)

    def file_exists(self, name) -> bool:
        return os.path.exists(os.path.join(self._dir, name))

    @property
    def ls(self) -> list[str]:
        return os.listdir(self._dir)

    @property
    def path(self) -> str:
        return self._dir

    @property
    def init_file(self) -> str:
        return ShipFile(self).full_name

    @property
    def last_round_number(self) -> int:
        last_round = -1
        pickle_files = fnmatch.filter(self.ls, '*.pickle')
        if len(pickle_files) > 0:
            last_round = max([int(n) for s in pickle_files for n in re.split('[-_. ]+', s) if n.isdigit()])
        return last_round


    def read_settings(self) -> dict:
        path = os.path.join(self._dir, SETTINGS_FILE_NAME)
        if not os.path.exists(path):
            return {}
        with open(path) as f:
            lines = [line for line in f if line.strip() and not line.lstrip().startswith('#')]
        return json.loads(lines[0]) if lines else {}

    def write_settings(self, settings: dict) -> None:
        with open(os.path.join(self._dir, SETTINGS_FILE_NAME), 'w') as f:
            f.write(json.dumps(settings, sort_keys=True) + '\n')

    def append_journal(self, entry: dict) -> None:
        """One line about something that happened to this game. The caller stamps the time."""
        with open(os.path.join(self._dir, JOURNAL_FILE_NAME), 'a') as f:
            f.write(json.dumps(entry) + '\n')

    def read_journal(self, limit: int = 0) -> list[dict]:
        """Oldest first. `limit` keeps the last that many."""
        path = os.path.join(self._dir, JOURNAL_FILE_NAME)
        if not os.path.exists(path):
            return []
        with open(path) as f:
            lines = [line for line in f if line.strip()]
        return [json.loads(line) for line in (lines[-limit:] if limit else lines)]

    def is_ready(self, player: str, round_nr: int) -> bool:
        path = os.path.join(self._dir, READY_FILE_TEMPLATE.format(player))
        if not os.path.exists(path):
            return False
        line = READY_LINE_TEMPLATE.format(round_nr)
        with open(path) as f:
            return any(l.strip() == line for l in f)

    def set_ready(self, player: str, round_nr: int, ready: bool) -> None:
        """A file per player, so two of them saying ready at once cannot race."""
        os.makedirs(os.path.join(self._dir, READY_DIR), exist_ok=True)
        path = os.path.join(self._dir, READY_FILE_TEMPLATE.format(player))
        line = READY_LINE_TEMPLATE.format(round_nr)
        lines = []
        if os.path.exists(path):
            with open(path) as f:
                lines = [l.strip() for l in f if l.strip() and l.strip() != line]
        if ready:
            lines.append(line)
        with open(path, 'w') as f:
            f.write('\n'.join(lines) + ('\n' if lines else ''))

    def command_file(self, name, round_nr) -> str:
        return CommandFile(self, name, round_nr).full_name

    def command_file_exists(self, name, round_nr) -> bool:
        return CommandFile(self, name, round_nr).exists

    def read_command_file(self, name, round_nr) -> list[str]:
        """Read a command file with the commands for a ship."""
        return CommandFile(self, name, round_nr).load()

    def status_file_for_round_exists(self, nr) -> bool:
        return StatusFile(self, nr).exists

    def status_file_for_round(self, nr) -> str:
        return StatusFile(self, nr).full_name

    @property
    def last_status_file(self) -> str:
        return StatusFile(self, self.last_round_number).full_name

    # ---------------------------------------------------------------------- QUERIES - Loading Data

    def load_current_world(self) -> World | None:
        if self.last_round_number > -1:
            return self.load_world(self.last_round_number)
        else:
            return None

    def load_world(self, round_nr) -> World:
        return StatusFile(self, round_nr).load()

    def missing_in(self, round_nr) -> dict:
        """What one saved round names that the code no longer has, and how often."""
        return StatusFile(self, round_nr).missing()

    def load_spawns(self) -> list[dict]:
        return SpawnFile(self).load()

    # ---------------------------------------------------------------------- COMMANDS

    def save_world(self, world: World, nr: int):
        StatusFile(self, nr).save(world)

    def append_spawn(self, record: dict):
        """A plan is added to rather than rewritten, unlike the world it will produce."""
        SpawnFile(self).append(record)

    def clean(self, keep_pickle_files=False):
        """Clean the game directory of all generated files."""
        types_to_remove = ['*.html', '*.png', '*.pdf', '*.pickle']
        if keep_pickle_files:
            types_to_remove = types_to_remove[:-1]
        for file_type in types_to_remove:
            for f in fnmatch.filter(self.ls, file_type):
                os.remove(os.path.join(self._dir, f))

        # Remove round directories
        for rd_dir in fnmatch.filter(self.ls, 'round*'):
            shutil.rmtree(os.path.join(self._dir, rd_dir))

    def setup_directories(self):
        if not os.path.exists(self._dir):
            os.mkdir(self._dir)
        cmd_dir = os.path.join(self._dir, COMMANDS_DIR)
        if not os.path.exists(cmd_dir):
            os.mkdir(cmd_dir)

    def check_ok(self):
        # Check if all is okay
        missing = [d for d in (self._dir, self.init_file) if not os.path.exists(d)]
        if missing:
            raise FileExistsError(f"{', '.join(missing)} not found.")


class GameFile(ABC):
    def __init__(self, gd: GameDirectory, name: str):
        self.gd = gd
        self._name = name

    @property
    def name(self):
        return self._name

    @property
    def full_name(self):
        return os.path.join(self.gd.path, self.name)

    @property
    def exists(self) -> bool:
        return self.gd.file_exists(self.name)

    def load(self) -> list:
        """Load file, one stripped line per list item"""
        with open(self.full_name) as f:
            return [line.strip() for line in f.readlines()]

    def save(self, contents):
        """Write file, one line per list item"""
        with open(self.full_name, 'w') as f:
            f.write('\n'.join(contents))


class JsonLinesFile(GameFile):
    """One JSON object per line, '#' starts a comment."""

    def load(self) -> list[dict]:
        records = list()
        for nr, line in enumerate(super().load(), start=1):
            if not line or line.startswith('#'):
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"{self.full_name} line {nr}: {e.msg}") from e
        return records


class ShipFile(JsonLinesFile):
    @dataclass
    class ShipFileLine:
        name: str
        type: str
        faction: str
        player: str = ''
        x: float = 0
        y: float = 0
        heading: float = 0

        @property
        def xy(self):
            return self.x, self.y

    def __init__(self, gd: GameDirectory, ships: list[dict] = None):
        """Ships as records: name, type, faction, and optionally player, x, y and heading."""
        super().__init__(gd, self.name)
        records = ships if ships is not None else self.load()
        self.ship_lines = [self.line_from_record(r) for r in records]

    @property
    def name(self):
        return INIT_FILE_NAME

    @staticmethod
    def line_from_record(record: dict):
        return ShipFile.ShipFileLine(
            name=record['name'],
            type=record['type'],
            faction=record['faction'],
            player=record.get('player', ''),
            x=record.get('x', 0),
            y=record.get('y', 0),
            heading=record.get('heading', 0),
        )

    def save(self, ships):
        super().save([json.dumps(self.record_for(ship)) for ship in ships])

    @staticmethod
    def record_for(ship) -> dict:
        record = {'name': ship.name, 'type': ship._type.__class__.__name__, 'faction': ship.faction}
        if ship.player:
            record['player'] = ship.player
        record['x'] = ship.pos.x
        record['y'] = ship.pos.y
        record['heading'] = ship.heading
        return record


class BodyFile(JsonLinesFile):
    """The terrain a game is played over: what is solid, and where it sits.

    Optional, because a game without any is a game on empty space. Nothing writes coordinates
    back the way ships do, since a body never moves off the ones it was given."""

    @dataclass
    class BodyFileLine:
        name: str
        type: str
        x: float = 0
        y: float = 0

        @property
        def xy(self):
            return self.x, self.y

    def __init__(self, gd: GameDirectory, bodies: list[dict] = None):
        super().__init__(gd, BODIES_FILE_NAME)
        records = bodies if bodies is not None else self.load()
        self.body_lines = [self.BodyFileLine(**r) for r in records]

    def load(self) -> list[dict]:
        return super().load() if self.exists else list()

    def save(self, bodies=None):
        super().save([json.dumps({'name': b.name, 'type': b.type, 'x': b.x, 'y': b.y})
                      for b in self.body_lines])


class SpawnFile(JsonLinesFile):
    """The plan for arrivals: what a director scheduled, and later what a scenario triggers.

    A plan is added to, never rewritten, so a line stands for one instruction that was given.
    What a ShipSpawner creates does not belong here: its Fire order is already the instruction,
    and a second record would spawn it twice on a replay."""

    def __init__(self, gd: GameDirectory):
        super().__init__(gd, SPAWN_FILE_NAME)

    def load(self) -> list[dict]:
        return super().load() if self.exists else list()

    def append(self, record: dict):
        with open(self.full_name, 'a') as f:
            f.write(json.dumps(record) + '\n')


class StatusFile(GameFile):
    """Pickle file with the state of the game between rounds."""
    def __init__(self, gd: GameDirectory, nr: int):
        self.nr = nr
        super().__init__(gd, self.name)

    @property
    def name(self):
        return STATUS_FILE_TEMPLATE.format(self.nr)

    @property
    def round(self) -> int:
        return self.nr

    def load(self) -> World:
        with open(self.full_name, 'rb') as f:
            try:
                world = pickle.load(f)
            except Exception as e:
                raise UnreadableWorld(self.gd.game_name, self.name) from e
        world.kept_in(self.gd)
        return world

    def save(self, world: World):
        assert isinstance(world, World)
        with open(self.full_name, 'wb') as status_file:
            pickle.dump(world, status_file)

    def missing(self) -> dict:
        """What this round names that the code no longer has, and how often."""
        with open(self.full_name, 'rb') as f:
            reader = _Stubbing(f)
            try:
                reader.load()
            except Exception as e:
                raise UnreadableWorld(self.gd.game_name, self.name) from e
        return reader.absent


class CommandFile(GameFile):
    """A player's command file for one ship for one round"""
    def __init__(self, gd: GameDirectory, ship_name: str, round_nr: int):
        self.ship_name = ship_name
        self.round_nr = round_nr
        super().__init__(gd, self.name)

    @property
    def name(self):
        return COMMAND_FILE_TEMPLATE.format(self.ship_name, self.round_nr)


GAMES_ROOT = GamesRoot(Path(GAME_DATA_DIR))
