import fnmatch
import os
import re
import shutil
import logging
from collections import namedtuple

from cfg import INIT_FILE_NAME, COMMAND_FILE_TEMPLATE, STATUS_FILE_TEMPLATE, EMAIL_CFG_NAME

logger = logging.getLogger(__name__)

InitLine = namedtuple('InitLine', 'name type x y player')


class GameDirectory(object):
    def __init__(self, data_root: str, game_name: str):
        self._dir = os.path.join(data_root, game_name)
        self.game_name = game_name

        with open(self.init_file) as infile:
            logger.info(f"Reading ship file {self.init_file}")
            self.init_lines = list()
            for line in [l for l in infile.readlines() if l.strip()]:
                if not line.startswith('#'):
                    split_line = line.strip().split()
                    assert len(split_line) == 5, f"Expected {split_line} to have 5 elements"
                    self.init_lines.append(InitLine(*split_line))

    @property
    def ls(self):
        return os.listdir(self._dir)

    @property
    def path(self):
        return self._dir

    @property
    def init_file(self):
        return os.path.join(self._dir, INIT_FILE_NAME)

    @property
    def last_round_number(self):
        last_round = -1
        pickle_files = fnmatch.filter(self.ls, '*.pickle')
        if len(pickle_files) > 0:
            last_round = max([int(n) for s in pickle_files for n in re.split('[-_. ]+', s) if n.isdigit()])
        return last_round

    @property
    def email_file(self):
        return os.path.join(self._dir, EMAIL_CFG_NAME)

    def command_file(self, name, round_nr):
        return os.path.join(self._dir, COMMAND_FILE_TEMPLATE.format(name, round_nr))

    def status_file_for_round(self, nr):
        return os.path.join(self._dir, STATUS_FILE_TEMPLATE.format(nr))

    @property
    def last_status_file(self):
        return self.status_file_for_round(self.last_round_number)

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

    def check_ok(self):
        # Check if all is okay
        if not os.path.exists(self._dir):
            sys.exit(f"{self._dir} not found.")
        if not os.path.exists(self.init_file):
            sys.exit(f"{self.init_file} not found.")
        if not os.path.exists(self.email_file):
            sys.exit(f"{self.email_file} not found.")

