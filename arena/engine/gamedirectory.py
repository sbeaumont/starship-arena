"""
Abstraction of a directory of a specific game of Space Arena.

- Hides all the specific information about structure and file names.
- Performs specific file operations on the directory.
"""

import fnmatch
import re
import shutil
import pickle
from dataclasses import dataclass
from abc import ABC

from arena.cfg import *
import logging

logger = logging.getLogger('starship-arena.gamedirectory')


class GameDirectory(object):
    def __init__(self, data_root: str, game_name: str):
        self._dir = os.path.join(data_root, game_name)
        self.game_name = game_name

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

    def get_turn_picture_name(self, round_nr, ship_name) -> str:
        relpath = os.path.join(self._dir, PICTURE_TEMPLATE.format(rnr=round_nr, name=ship_name))
        return os.path.abspath(relpath)

    def get_turn_pdf_name(self, round_nr, ship_name) -> str:
        relpath = os.path.join(self._dir, PDF_TEMPLATE.format(rnr=round_nr, name=ship_name))
        return os.path.abspath(relpath)

    @property
    def email_file(self) -> str:
        return os.path.join(self._dir, EMAIL_CFG_NAME)

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

    def round_dir(self, round_nr: int):
        return RoundDirectory(self, round_nr)

    # ---------------------------------------------------------------------- QUERIES - Loading Data

    def load_current_status(self) -> dict | None:
        if self.last_round_number > -1:
            return self.load_status(self.last_round_number)
        else:
            return None

    def load_status(self, round_nr) -> dict:
        return StatusFile(self, round_nr).load()

    def load_graveyard(self) -> dict:
        graveyard = GraveyardFile(self)
        if graveyard.exists:
            return graveyard.load()
        else:
            return dict()

    # ---------------------------------------------------------------------- COMMANDS

    def save(self, obj, nr):
        StatusFile(self, nr).save(obj)

    def save_graveyard(self, obj: dict):
        GraveyardFile(self).save(obj)

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


class ShipFile(GameFile):
    @dataclass
    class ShipFileLine:
        name: str
        type: str
        faction: str
        player: str = ''
        x: float = 0
        y: float = 0

        def move(self, xy: tuple):
            self.x += xy[0]
            self.y += xy[1]
            return self

        @property
        def xy(self):
            return self.x, self.y

        def __str__(self):
            return f"{self.name},{self.type},{self.faction},{self.player},{round(self.x)},{round(self.y)}"

    def __init__(self, gd: GameDirectory, premade_lines: str = None):
        super().__init__(gd, self.name)
        text_lines = [line.strip().split() for line in premade_lines.splitlines()] if premade_lines else self.load()
        self.ship_lines = self.ship_lines_to_objects(text_lines)

    @property
    def name(self):
        return INIT_FILE_NAME

    def load(self) -> list:
        return [line.split() for line in super().load()]

    def save(self, ships):
        assert isinstance(ships, list) or isinstance(ships, type(dict().values()))
        super().save(self.ship_file_with_coordinates(ships))

    @staticmethod
    def ship_lines_to_objects(lines: list):
        field_defs = {sl[1]: sl[0] for sl in enumerate(lines[0])}
        ships = list()
        for line in lines[1:]:
            try:
                if line[0].strip().startswith('#'):
                    # Ignore lines that start with #
                    continue
                ship = ShipFile.ShipFileLine(
                    name=line[field_defs['Name']],
                    type=line[field_defs['Type']],
                    faction=line[field_defs['Faction']],
                    player=line[field_defs['Player']]
                )
                if 'X' in field_defs and 'Y' in field_defs:
                    x = int(line[field_defs['X']])
                    y = int(line[field_defs['Y']])
                    ship.move((x, y))
                ships.append(ship)
            except (KeyError, ValueError):
                logger.error(f"Failed to process <{line}>")
                print(line)
                raise
        return ships

    @staticmethod
    def ship_file_with_coordinates(ships: list):
        fields = ['name', 'type', 'faction', 'player', 'x', 'y']
        max_lengths = {
            'name': max(max([len(s.name) for s in ships]), len('name')),
            'type': max(max([len(s._type.__class__.__name__) for s in ships]), len('type')),
            'faction': max(max([len(s.faction) for s in ships]), len('faction')),
            'player': max(max([len(s.player) for s in ships]), len('player')),
            'x': max(max([len(str(s.pos.x)) for s in ships]), len('x')),
            'y': max(max([len(str(s.pos.y)) for s in ships]), len('y'))
        }

        lines = list()
        header_line = ' '.join([fieldname.capitalize().rjust(max_lengths[fieldname]) for fieldname in fields])
        lines.append(header_line)
        for ship in ships:
            line_values = {
                'name': ship.name,
                'type': ship._type.__class__.__name__,
                'faction': ship.faction,
                'player': ship.player,
                'x': ship.pos.x,
                'y': ship.pos.y
            }
            ship_line = ' '.join([str(line_values[fieldname]).rjust(max_lengths[fieldname]) for fieldname in fields])
            lines.append(ship_line)
        return lines


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

    def load(self) -> dict:
        with open(self.full_name, 'rb') as f:
            return pickle.load(f)

    def save(self, ships):
        assert isinstance(ships, dict)
        with open(self.full_name, 'wb') as status_file:
            pickle.dump(ships, status_file)


class GraveyardFile(StatusFile):
    """File with dead ships for reporting"""
    def __init__(self, gd: GameDirectory):
        super().__init__(gd, -1)

    @property
    def name(self):
        return GRAVEYARD_TEMPLATE


class CommandFile(GameFile):
    """A player's command file for one ship for one round"""
    def __init__(self, gd: GameDirectory, ship_name: str, round_nr: int):
        self.ship_name = ship_name
        self.round_nr = round_nr
        super().__init__(gd, self.name)

    @property
    def name(self):
        return COMMAND_FILE_TEMPLATE.format(self.ship_name, self.round_nr)


class RoundDirectory(object):
    def __init__(self, gd: GameDirectory, round_nr: int):
        self.gd = gd
        self.name = ROUND_DIR_TEMPLATE.format(rnr=round_nr)
        self.round_nr = round_nr

        if not self.exists:
            os.mkdir(self.full_name)

    @property
    def full_name(self):
        return os.path.join(self.gd.path, self.name)

    @property
    def exists(self):
        return os.path.exists(self.full_name)

    def save(self, filename, contents, binary=False):
        mode = 'wb' if binary else 'w'
        with open(os.path.join(self.full_name, filename), mode) as f:
            f.write(contents)

    def load(self, filename):
        with open(os.path.join(self.full_name, filename)) as f:
            return f.read()
