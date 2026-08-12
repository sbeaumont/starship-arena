"""What the checks have to say about one file. The hook's entry point.

Run as `python -m test.docs.check_file <path>`. Exits 2 with the findings on stderr so the
editor that just wrote the file hears about it, and 0 when the file is clean.
"""

import sys
from pathlib import Path

from arena.cfg import REPO_ROOT
from test.docs.test_comments import narrating
from test.docs.test_references import broken, prose
from test.engine.test_vocabulary import inspections

ROOT = Path(REPO_ROOT)


def findings_for(path: Path) -> list:
    """Only what the checks say about this one file, so an old failure elsewhere stays quiet."""
    here = str(path.relative_to(ROOT))
    found = []
    if path.suffix == '.md' and path in prose():
        found += [row for row in broken() if row.startswith(f"{here}:")]
    if path.suffix == '.py':
        found += [f"{p}:{line} branches on whether something is {' or '.join(asked)}; the object "
                  f"answers for itself, so ask it"
                  for p, line, asked, anchored in inspections() if str(p) == here and not anchored]
        found += [row for row in narrating() if row.startswith(f"{here}:")]
    return found


if __name__ == '__main__':
    target = Path(sys.argv[1]).resolve()
    if not target.is_relative_to(ROOT) or not target.exists():
        sys.exit(0)

    problems = findings_for(target)
    if problems:
        print('\n'.join(problems), file=sys.stderr)
        sys.exit(2)