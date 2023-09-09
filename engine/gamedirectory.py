import fnmatch
import os
import re
import shutil
import logging
import pickle
from collections import namedtuple

from cfg import INIT_FILE_NAME, COMMAND_FILE_TEMPLATE, COMMANDS_DIR,\
                 STATUS_FILE_TEMPLATE, EMAIL_CFG_NAME, PICTURE_TEMPLATE, PDF_TEMPLATE

logger = logging.getLogger('starship-arena.gamedirectory')

InitLine = namedtuple('InitLine', 'name type faction player')


class GameDirectory(object):
    def __init__(self, data_root: str, game_name: str):
        self._dir = os.path.join(data_root, game_name)
        self.game_name = game_name

    # ---------------------------------------------------------------------- QUERIES - Filenames

    @property
    def ls(self) -> list[str]:
        return os.listdir(self._dir)

    @property
    def path(self) -> str:
        return self._dir

    @property
    def init_file(self) -> str:
        return os.path.join(self._dir, INIT_FILE_NAME)

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
        return os.path.join(self._dir, COMMAND_FILE_TEMPLATE.format(name, round_nr))

    def command_file_exists(self, name, round_nr) -> bool:
        return os.path.exists(self.command_file(name, round_nr))

    def status_file_for_round(self, nr) -> str:
        return os.path.join(self._dir, STATUS_FILE_TEMPLATE.format(nr))

    @property
    def last_status_file(self) -> str:
        return self.status_file_for_round(self.last_round_number)

    # ---------------------------------------------------------------------- QUERIES - Loading Data

    def load_current_status(self) -> dict | None:
        if self.last_round_number > -1:
            return self.load_status(self.last_round_number)
        else:
            return None

    def load_status(self, round_nr) -> dict:
        status_file_name = self.status_file_for_round(round_nr)
        with open(status_file_name, 'rb') as f:
            return pickle.load(f)

    # ---------------------------------------------------------------------- COMMANDS

    def save(self, obj, nr):
        status_file_name = self.status_file_for_round(nr)
        with open(status_file_name, 'wb') as status_file:
            pickle.dump(obj, status_file)

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
        missing = [d for d in (self._dir, self.init_file, self.email_file) if not os.path.exists(d)]
        if missing:
            raise FileExistsError(f"{','.join(missing)} not found.")
