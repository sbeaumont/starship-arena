"""No scenario at all: a name and an empty roster you fill in yourself."""

from arena.app.scenarios.placement import distribute_factions

FACTION_DISTANCE = 500


class GenericGame:
    key = 'generic'
    name = 'Generic Game'
    blurb = ("Nothing decided for you. Name it, type the roster yourself, and pick every ship and "
             "faction by hand. What to use when a scenario would only get in the way.")
    factions = []
    max_ships = 0
    registers = False

    def deal(self, entries, rng) -> list[dict]:
        return []

    def place(self, ships: list[dict], rng) -> list[dict]:
        """Whatever factions the typed roster turned out to have, spread around the middle."""
        return distribute_factions(ships, rng, FACTION_DISTANCE)

    def bodies(self, rng=None) -> list[dict]:
        return []

    def outcome(self, world) -> None:
        """Nothing decided for you here either. The director closes it."""
        return None

    def charted_for(self, world, factions) -> list:
        return []