"""What the host installs is what the project declares.

`pyproject.toml` is where a dependency is decided and `requirements.txt` is the copy the host can
read, because it runs a Python with no tomllib. A copy nothing checks is a copy that goes stale
the first time somebody adds a package, and the way that shows up is a 500 on the host.
"""

import tomllib
import unittest
from pathlib import Path

from arena.cfg import REPO_ROOT

ROOT = Path(REPO_ROOT)


def declared() -> list:
    with open(ROOT / 'pyproject.toml', 'rb') as f:
        return tomllib.load(f)['project']['dependencies']


def installed_on_the_host() -> list:
    return [line.strip() for line in (ROOT / 'requirements.txt').read_text().splitlines()
            if line.strip() and not line.startswith('#')]


class TestTheHostInstallsWhatTheProjectDeclares(unittest.TestCase):

    def test_the_two_lists_are_the_same(self):
        self.assertEqual(declared(), installed_on_the_host(),
                         "pyproject.toml and requirements.txt disagree. pyproject decides; write "
                         "its dependencies into requirements.txt, one per line, same order.")