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
        # Everyone commands at least one ship and nobody gets more than they asked for, so the
        # level a faction can be held to is bounded on both sides.
        target = max(max(len(m) for m in dealt.values()),
                     min(sum(e.ships for e in m) for m in dealt.values()))
        return [record
                for faction, members in dealt.items()
                for record in self._faction_records(faction, members, target, rng)]

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
    def _granted(members: list[Registration], target: int, rng) -> dict[str, int]:
        granted = {e.player: 1 for e in members}
        extras = [e.player for e in members for _ in range(e.ships - 1)]
        rng.shuffle(extras)
        total = len(members)
        for player in extras[:max(0, target - total)]:
            granted[player] += 1
        return granted

    def _faction_records(self, faction: str, members: list[Registration], target: int, rng) -> list[dict]:
        granted = self._granted(members, target, rng)
        hulls = FACTIONS[faction]
        records, flown = [], 0
        for entry in members:
            for nth in range(granted[entry.player]):
                name = entry.names[nth] if nth < len(entry.names) else f"{faction}-{flown + 1}"
                records.append({'name': name, 'type': hulls[flown % len(hulls)],
                                'faction': faction, 'player': entry.player})
                flown += 1
        # Members are already in the shuffled deal order, so a tie on ship count breaks randomly.
        commander = min(members, key=lambda e: granted[e.player]).player
        records.append({'name': f"{faction}-Base", 'type': STARBASE,
                        'faction': faction, 'player': commander})
        return records