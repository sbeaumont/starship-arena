"""One commander, three pirate hulls, and the five rocks everybody flies around.

A game a player starts on their own, so there is something to fly before a war is being set up.
Nobody else has to be ready, so a round runs the moment they say so.
See docs/adr/0030-solo-games-live-in-their-own-root.md.
"""

from arena.app.scenarios.terrain import asteroid_ring
from arena.engine.objects.registry.builder import all_ship_types

RING_RADIUS = 250

PLAYER_FACTION = 'Patrol'
OPPOSITION = 'Pirates'

# Where each of the four starts is the whole of this scenario's design, so the spots are written
# out rather than derived. The patrol comes up from below the ring, far enough out that the first
# round is a run-in. The pirates hold the middle, the gap between the two upper-left rocks, and
# the space outside the upper-right one: three approaches, each asking something different.
SPOTS = {
    PLAYER_FACTION: [(-20, -400), (20, -400)],
    OPPOSITION: [(0, 0), (-119, 164), (304, 99)],
}
FACING = {PLAYER_FACTION: 0, OPPOSITION: 180}


class SoloGame:
    key = 'solo'
    name = 'Solo Game'
    blurb = ("A ship or two of your own against three pirate hulls among the asteroids. Nobody "
             "else has to be ready: say you are done and the round runs. Somewhere to learn the "
             "map, the orders and the weapons before a war starts.")
    factions = list(SPOTS)
    max_ships = len(SPOTS[PLAYER_FACTION])
    registers = False

    def bodies(self) -> list[dict]:
        """The same five rocks the war is fought over, so practice is practice for that."""
        return asteroid_ring(RING_RADIUS)

    def deal(self, entries, rng) -> list[dict]:
        """Nobody registers for a solo game. Its roster comes from what the player picked."""
        return []

    def roster(self, player: str, picks: list[dict], rng) -> list[dict]:
        """The hulls the player chose, and three the pirates turned up in.

        What they meet is drawn rather than fixed, so starting over is a different game."""
        if not 1 <= len(picks) <= self.max_ships:
            raise ValueError(f"A solo game flies 1 to {self.max_ships} ships, not {len(picks)}.")
        for pick in picks:
            if not pick['name'].strip():
                raise ValueError("Every ship needs a name.")
            if pick['type'] not in all_ship_types:
                raise ValueError(f"'{pick['type']}' is not a ship anybody flies.")

        ships = [{'name': pick['name'].strip(), 'type': pick['type'],
                  'faction': PLAYER_FACTION, 'player': player} for pick in picks]
        ships += [{'name': f"{OPPOSITION}-{n + 1}", 'type': hull, 'faction': OPPOSITION}
                  for n, hull in enumerate(rng.sample(sorted(all_ship_types),
                                                      len(SPOTS[OPPOSITION])))]
        names = [s['name'] for s in ships]
        if len(set(names)) != len(names):
            raise ValueError("Two ships in one game cannot share a name.")
        return ships

    def place(self, ships: list[dict], rng) -> list[dict]:
        """Everybody on their own spot, in the order the roster built them."""
        spots = {faction: iter(where) for faction, where in SPOTS.items()}
        placed = []
        for ship in ships:
            x, y = next(spots[ship['faction']])
            placed.append(dict(ship, x=x, y=y, heading=FACING[ship['faction']]))
        return placed