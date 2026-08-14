"""Scenarios the director can start a game from.

A scenario turns a list of people into a roster. The knowledge that a race is a faction lives
here rather than in the engine: see plans/scenario-setup-plan.md.
"""

from arena.app.scenarios.five_faction_war import FiveFactionWar
from arena.app.scenarios.generic import GenericGame
from arena.app.scenarios.solo import SoloGame
from arena.app.scenarios.vip_escort import VipEscort

# What a director can start a game from. The solo scenario is not one of them: a player starts
# their own, from hulls they pick, in a root of its own.
# See docs/adr/0030-solo-games-live-in-their-own-root.md.
ALL = [FiveFactionWar(), VipEscort(), GenericGame()]
SOLO = SoloGame()


def by_key(key: str):
    found = [s for s in [*ALL, SOLO] if s.key == key]
    if not found:
        raise KeyError(f"'{key}' is not a scenario.")
    return found[0]