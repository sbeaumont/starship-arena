"""No scenario at all: a name and an empty roster you fill in yourself."""


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
