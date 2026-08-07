"""Five factions, one war. Everybody who plays is dealt into one of them."""

from math import cos, radians, sin

from arena.app.registrations import Registration

# Factions start on a circle of radius 500, so a ring half way in leaves everyone the same choice:
# go around the outside, or cut through the middle and thread the gaps.
RING_RADIUS = 250
RING_BODIES = 5

FACTIONS = {
    'Human': ['H2545', 'H2552', 'H2535', 'H2527'],
    'Feline': ['F2551', 'F2547', 'F2534', 'F2533'],
    'Amphibian': ['A2527', 'A2539', 'A2545', 'A2553'],
    'Reptilian': ['R2545', 'R2525', 'R2531', 'R2551'],
    'Insectoid': ['I2544', 'I2552', 'I2526'],
}

STARBASE = 'SB2531'


class FiveFactionWar:
    key = 'five-faction-war'
    name = 'The Five Faction War'
    blurb = ("All five factions at each other's throats. Everyone flies their faction's own line "
             "of hulls. Every faction gets a starbase, and one of its own commands it.")
    factions = list(FACTIONS)
    max_ships = 3
    registers = True

    def bodies(self) -> list[dict]:
        """A ring of asteroids between the factions and the middle."""
        return [{'name': f"Asteroid-{n + 1}", 'type': 'Asteroid',
                 'x': round(RING_RADIUS * sin(radians(n * 360 / RING_BODIES))),
                 'y': round(RING_RADIUS * cos(radians(n * 360 / RING_BODIES)))}
                for n in range(RING_BODIES)]

    def deal(self, entries: list[Registration], rng) -> list[dict]:
        """Ship records for everyone, each in the faction they were assigned to or dealt into."""
        unknown = {e.faction for e in entries if e.faction} - set(FACTIONS)
        if unknown:
            raise ValueError(f"Not a faction in this scenario: {', '.join(sorted(unknown))}.")
        if not entries:
            raise ValueError("Nobody has registered.")

        dealt = self._deal_players(entries, rng)
        return [record
                for faction, members in dealt.items()
                for record in self._faction_records(faction, members)]

    def _deal_players(self, entries: list[Registration], rng) -> dict[str, list[Registration]]:
        """Honour what the director assigned, then spread the rest to even the head count.

        A faction nobody lands in is not in the game, which is the only way this asks which
        factions are playing."""
        dealt = {faction: [] for faction in FACTIONS}
        pool = []
        for entry in entries:
            if entry.faction:
                dealt[entry.faction].append(entry)
            else:
                pool.append(entry)
        for entry in rng.sample(pool, len(pool)):
            dealt[min(dealt, key=lambda f: len(dealt[f]))].append(entry)
        return {faction: members for faction, members in dealt.items() if members}

    @staticmethod
    def _faction_records(faction: str, members: list[Registration]) -> list[dict]:
        """Everybody flies every ship they registered. Balancing the factions is the director's."""
        hulls = FACTIONS[faction]
        records = []
        for entry in members:
            for name in entry.names:
                records.append({'name': name, 'type': hulls[len(records) % len(hulls)],
                                'faction': faction, 'player': entry.player})
        # Members are already in the shuffled deal order, so a tie on ship count breaks randomly.
        commander = min(members, key=lambda e: e.ships).player
        records.append({'name': f"{faction}-Base", 'type': STARBASE,
                        'faction': faction, 'player': commander})
        return records