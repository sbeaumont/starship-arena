"""A comment describes the present. Anything comparing it to a past belongs in git."""

import re
import unittest
from pathlib import Path

from arena.cfg import REPO_ROOT
from test.docs.test_references import walk

# Wording that only makes sense to somebody who saw the previous version.
NARRATES_A_CHANGE = re.compile(
    r'\b(no longer|used to|previously|formerly|as before|this replaces|changed from'
    r'|moved from|renamed from|was called|now returns|now takes|now uses|now lives'
    r'|now sits|we now|has become)\b', re.IGNORECASE)

COMMENT = re.compile(r'#\s*(.*)$')


def narrating() -> list:
    """Comments written against a version of the code that nobody can see."""
    found = []
    for path in walk(frozenset({'.py'})):
        for number, line in enumerate(path.read_text().splitlines(), 1):
            stripped = line.strip()
            if not stripped.startswith('#'):
                continue
            text = COMMENT.match(stripped).group(1)
            hit = NARRATES_A_CHANGE.search(text)
            if hit:
                found.append(f"{path.relative_to(Path(REPO_ROOT))}:{number} "
                             f"\"{hit.group(1)}\" — {text[:60]}")
    return found


class TestCommentsDescribeThePresent(unittest.TestCase):
    """A reader of this line has never seen what it used to say."""

    def test_no_comment_narrates_its_own_change(self):
        found = narrating()

        if found:
            self.fail("comments comparing the code to a version git already holds:\n  "
                      + '\n  '.join(found))


if __name__ == '__main__':
    rows = narrating()
    print(f"=== NARRATING ({len(rows)}) ===")
    for row in rows:
        print(f"  {row}")