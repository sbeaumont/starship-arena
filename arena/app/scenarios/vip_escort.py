"""One side walks a VIP across the map. The other side makes sure it never gets there."""

import logging
import random

from arena.app.dto import Outcome
from arena.app.registrations import Registration
from arena.app.scenarios.terrain import scatter
from arena.engine.objects.registry.builder import all_ship_types

logger = logging.getLogger('starship-arena.scenarios')

# Both sides fly whatever they like. Nobody is defending a homeworld here, and a hunter is
# whatever turned up for the money.
FACTIONS = ['Escort', 'Hunters']

# What settling the mission is worth, split across the commanders of the side that settled it.
# Read against a kill, which is 100 to whoever landed the blow.
OBJECTIVE = 500

VIP_HULL = 'C2540'
VIP_NAME = 'Envoy'
BEACON = 'JumpPoint'
BEACON_NAME = 'Jump Point'

# A board in three across its short side: the escort starts in the west, the hunters wait in the
# middle, and the way out is somewhere in the east. Tall rather than wide on purpose. The run is
# what a hunter has to cover and wants to be short; the room to go around them runs the other way
# and wants to be long.
WIDTH, HEIGHT = 1800, 2500
THIRD = WIDTH / 3

# Far enough from an edge that the way out is never in a corner nobody would sweep.
BEACON_MARGIN = 100

# Dense enough to be a maze at a full sweep of 346, and open enough to fly at speed. Dropping
# them at random rather than packing them saturates at about 220 over a board this size, so this
# is most of what fits and raising it much further will not place at all.
ROCK = 'Boulder'
ROCKS = 175
ROCKS_APART = 120

# The escort comes in from outside the field, strung out over its whole height with a band each,
# because a group is a sighting that gives the VIP away: find one hull and you have found them all.
# Starting clear of the rocks is also what saves the field from having to leave a lane for them.
ESCORT_STANDOFF = 150
ESCORT_X = -WIDTH / 2 - ESCORT_STANDOFF
ESCORT_BAND = HEIGHT * 0.9
HUNTER_START = (0, 0)
SPREAD = 30
FACING = {'Escort': 90, 'Hunters': 270}

# Fields worth playing, found by starting games and looking at the map. An empty list draws a
# fresh one and logs it, which is how this fills up.
SEEDS = []


class VipEscort:
    key = 'vip-escort'
    name = 'VIP Escort'
    blurb = ("One ship has to reach a jump point on the far side of an asteroid field, and one "
             "side is paid to see that it does not. The VIP carries no gun worth the name: it is "
             "quick on the helm, it can go dark, and it leaves mines behind it. Everyone else "
             "flies whatever they like.")
    factions = list(FACTIONS)
    max_ships = 2
    registers = True

    def bodies(self, rng) -> list[dict]:
        """A field of rocks, and the way out somewhere in the east third.

        The rocks are drawn from a seed of their own so that a field worth playing can be kept,
        while which side the escort starts on stays a fresh draw every game."""
        beacon = (rng.uniform(THIRD / 2 + BEACON_MARGIN, WIDTH / 2 - BEACON_MARGIN),
                  rng.uniform(-HEIGHT / 2 + BEACON_MARGIN, HEIGHT / 2 - BEACON_MARGIN))
        seed = rng.choice(SEEDS) if SEEDS else rng.randrange(1_000_000)
        logger.info(f"{self.key}: asteroid field from seed {seed}")
        field = scatter(random.Random(seed), ROCKS, WIDTH, HEIGHT, ROCKS_APART, body=ROCK,
                        clear_of=[HUNTER_START, beacon])
        return field + [{'name': BEACON_NAME, 'type': BEACON,
                         'x': round(beacon[0]), 'y': round(beacon[1])}]

    def place(self, ships: list[dict], rng) -> list[dict]:
        """The escort strung out along the western edge, the hunters together in the middle.

        A band each and the bands dealt at random, so which of them is carrying the VIP is not
        something a hunter can read off the formation."""
        escort = [s for s in ships if s['faction'] == 'Escort']
        bands = rng.sample(range(len(escort)), len(escort))
        band_height = ESCORT_BAND / len(escort)
        spots = {}
        for ship, band in zip(escort, bands):
            spots[ship['name']] = (
                ESCORT_X + rng.uniform(-SPREAD, SPREAD),
                -ESCORT_BAND / 2 + (band + rng.random()) * band_height)
        placed = []
        for ship in ships:
            if ship['name'] in spots:
                x, y = spots[ship['name']]
            else:
                spot = len([s for s in placed if s['faction'] == ship['faction']])
                x = HUNTER_START[0] + rng.uniform(-SPREAD, SPREAD)
                y = HUNTER_START[1] + spot * SPREAD - SPREAD
            placed.append(dict(ship, heading=FACING[ship['faction']], x=round(x), y=round(y)))
        return placed

    def charted_for(self, world, factions) -> list:
        """The escort was briefed and knows the way out. The hunters have to find it.

        That is the asymmetry the mission is built on: one side plans a route, the other has to
        work out which one."""
        if 'Escort' not in factions:
            return []
        return [o for o in world.objects.values() if o.type_name == BEACON]

    def outcome(self, world) -> Outcome | None:
        """Over when the VIP has docked or has been destroyed, and nothing else ends it.

        The objective is paid to the side that settled it, split across its commanders, and it is
        a separate tally from what anybody shot: see work/plans/vip-escort-plan.md."""
        vip = next((o for o in world.all_objects.values() if o.type_name == VIP_HULL), None)
        if vip is None:
            return None
        beacon = next((o for o in world.all_objects.values() if o.type_name == BEACON), None)
        if beacon is not None and vip.name in beacon.docked:
            return self._won_by('Escort', f"{vip.name} reached {beacon.name}.", world)
        if vip.is_destroyed:
            return self._won_by('Hunters', f"{vip.name} was destroyed.", world)
        return None

    @staticmethod
    def _won_by(faction: str, reason: str, world) -> Outcome:
        """The objective, split across the winning side's commanders, whatever they flew."""
        crew = sorted({o.player for o in world.all_objects.values()
                       if o.faction == faction and o.player})
        return Outcome(faction=faction, reason=reason,
                       points={player: OBJECTIVE // len(crew) for player in crew})

    def deal(self, entries: list[Registration], rng) -> list[dict]:
        """Ship records for everyone, with the VIP added to whoever has the smallest fleet."""
        unknown = {e.faction for e in entries if e.faction} - set(FACTIONS)

        if unknown:
            raise ValueError(f"Not a faction in this scenario: {', '.join(sorted(unknown))}.")
        if not entries:
            raise ValueError("Nobody has registered.")

        dealt = self._deal_players(entries, rng)
        if 'Escort' not in dealt:
            raise ValueError("Nobody is escorting the VIP.")
        records = [record
                   for faction, members in dealt.items()
                   for record in self._faction_records(faction, members, rng)]
        carrier = min(dealt['Escort'], key=lambda e: e.ships).player
        return records + [{'name': VIP_NAME, 'type': VIP_HULL,
                           'faction': 'Escort', 'player': carrier}]

    @staticmethod
    def _deal_players(entries: list[Registration], rng) -> dict[str, list[Registration]]:
        """Honour what the director assigned, then even out the head count."""
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
    def _faction_records(faction: str, members: list[Registration], rng) -> list[dict]:
        """A hull each, drawn from everything anybody flies. The director can still change it."""
        hulls = sorted(set(all_ship_types) - {VIP_HULL})
        return [{'name': name, 'type': rng.choice(hulls),
                 'faction': faction, 'player': entry.player}
                for entry in members for name in entry.names]