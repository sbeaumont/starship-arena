"""A game as it was played, in text that outlives the code that played it.

One package per version of the format. The newest writes, every one of them reads, and a file
says which version it is.
See docs/adr/0034-a-finished-game-is-exported-to-a-schema-of-its-own.md.
"""

import json

from arena.app.valhalla import v1

NEWEST = v1                     # the only version anything writes
READERS = {v1.VERSION: v1}      # every version there has ever been


def export(replay, game: str) -> str:
    """A played game, written out in the newest version of the format."""
    return json.dumps(NEWEST.write(replay, game), indent=1)


def load(text: str) -> dict:
    """A file, in the shape its own version promises. Any other version is refused by number."""
    raw = json.loads(text)
    version = raw.get('version')
    if version not in READERS:
        raise ValueError(f"Valhalla format version {version} is not one this code can read.")
    return READERS[version].read(raw)