"""Scenarios the director can start a game from.

A scenario turns a list of people into a roster. The knowledge that a race is a faction lives
here rather than in the engine: see plans/scenario-setup-plan.md.
"""

from arena.app.scenarios.five_faction_war import FiveFactionWar
from arena.app.scenarios.generic import GenericGame

ALL = [FiveFactionWar(), GenericGame()]


def by_key(key: str):
    found = [s for s in ALL if s.key == key]
    if not found:
        raise KeyError(f"'{key}' is not a scenario.")
    return found[0]