"""A game's name on disk, and the name a person reads.

One is derived from the other, so a game carries no separate title to keep in step."""

import re


def as_stored(name: str) -> str:
    """`Faction War  2` becomes `Faction_War_2`, which can be a directory."""
    return re.sub(r'\s+', '_', name.strip())


def for_display(name: str) -> str:
    return name.replace('_', ' ')


# Reserved, so a shared game can never be named what somebody's own game is or could be called.
# Player names are unique, so the whole set of solo names is spoken for by this one word.
SOLO_PREFIX = 'Solo'


def solo_game_name(player: str) -> str:
    """A player's own game names itself, so there can only ever be one of them."""
    return as_stored(f"{SOLO_PREFIX} {player}")


def is_solo_game_name(name: str) -> bool:
    """Whether a name belongs to somebody's own game, whether or not they have started one."""
    return as_stored(name).startswith(f"{SOLO_PREFIX}_")