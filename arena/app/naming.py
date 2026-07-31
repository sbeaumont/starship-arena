"""A game's name on disk, and the name a person reads.

One is derived from the other, so a game carries no separate title to keep in step."""

import re


def as_stored(name: str) -> str:
    """`Faction War  2` becomes `Faction_War_2`, which can be a directory."""
    return re.sub(r'\s+', '_', name.strip())


def for_display(name: str) -> str:
    return name.replace('_', ' ')