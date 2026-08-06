"""Reads the ship registry and reports what each model is worth.

Every number here is derived from the registry and the component code, never typed in twice.
The assumptions that are judgement calls sit in the block at the top, so they can be argued with.
"""

import math
from collections import defaultdict

from arena.engine.objects.registry import builder
from arena.engine.objects.components.defense import Shields
from arena.engine.objects.components.ecm import Cloak
from arena.engine.objects.components.laser import Laser
from arena.engine.objects.components.launcher import Launcher
from arena.engine.objects.components.scanner import Gravscan
from arena.engine.objects.components.spawner import ShipSpawner
from arena.engine.objects.components.warhead import DamageType
from arena.engine.objects.mine import Mine
from arena.engine.objects.missile import GuidedMissile
from arena.app.scenarios.five_faction_war import FACTIONS

# ---------------------------------------------------------------- TWEAKABLE ASSUMPTIONS

TICKS_PER_ROUND = 10

# Where a laser is assumed to be used. Damage falls off squared to nothing at its reach, so a
# laser scored at the range missiles cross would read as worthless. Missiles are scored at
# contact, which means the two weapon classes are each judged in their own band.
LASER_RANGE = 20

# How much of a payload's damage actually lands. A guided missile steers onto its target; a
# dumb rocket has to be aimed at where the target will be. Mines are area denial, not offense.
DELIVERY = {'guided': 1.0, 'dumb': 0.45, 'mine': 0.0}

# A weapon locked to an arc still fires, it just has to be pointed. This is the worst it gets:
# a 90-degree arc is worth this much of what a turret is worth.
ARC_FLOOR = 0.55

# Weights of the composite score, as a weighted geometric mean of fleet-relative metrics.
WEIGHTS = {'offense': 0.40, 'defense': 0.35, 'mobility': 0.15, 'economy': 0.10}


# ---------------------------------------------------------------- READING THE REGISTRY

def arc_fraction(firing_arc):
    if not firing_arc:
        return 1.0
    left, right = firing_arc
    return ((right - left) % 360 or 360) / 360


def arc_weight(firing_arc):
    """What an arc-limited weapon is worth against a turret, ARC_FLOOR at its narrowest."""
    return ARC_FLOOR + (1 - ARC_FLOOR) * arc_fraction(firing_arc)


def payload_class(payload_type):
    base = payload_type.base_type
    if issubclass(base, Mine):
        return 'mine'
    return 'guided' if issubclass(base, GuidedMissile) else 'dumb'


def warhead_of(payload_type):
    return payload_type.weapons[0]


def payload_reach(payload_type):
    """How far a payload can fly before its battery runs out."""
    if payload_class(payload_type) == 'mine':
        return 0
    ticks = payload_type.start_battery // payload_type.energy_per_move
    return ticks * payload_type.max_speed


def damage_vs(warhead, target):
    """What one warhead does to a shielded target, and to bare hull.

    Nanocytes cannot pass a shield with any strength left at all, and double against hull.
    An EMP does double to a shield and nothing to hull; it drains the battery instead.
    """
    d = warhead.damage
    if warhead.damage_type == DamageType.Nanocyte:
        return 0 if target == 'shield' else 2 * d
    if warhead.damage_type == DamageType.EMP:
        return 2 * d if target == 'shield' else 0
    return d


def laser_shots_from_cold(laser):
    """How often a laser fires in a round, starting cool. Heat is the limit, not energy."""
    temperature, shots = 0, 0
    for _ in range(TICKS_PER_ROUND):
        temperature = max(0, temperature - 5)
        if temperature <= laser.max_temperature:
            shots += 1
            temperature += laser.heat_per_shot
    return shots


def laser_damage(laser, distance=LASER_RANGE):
    if distance >= laser.reach:
        return 0
    return round(laser.damage * (1 - distance / laser.reach) ** 2)


class Profile(object):
    """Everything worth knowing about one ship model."""

    def __init__(self, ship_type):
        self.t = ship_type
        self.name = ship_type.type_name
        self.class_name = ship_type.class_name

        self.lasers = [w for w in ship_type.weapons if isinstance(w, Laser)]
        self.launchers = [w for w in ship_type.weapons if isinstance(w, Launcher)]
        self.gravscans = [w for w in ship_type.weapons if isinstance(w, Gravscan)]
        self.spawners = [w for w in ship_type.weapons if isinstance(w, ShipSpawner)]
        self.shields = next((d for d in ship_type.defense if isinstance(d, Shields)), None)
        self.cloak = next((e for e in ship_type.ecm if isinstance(e, Cloak)), None)

        self.attack_launchers = [l for l in self.launchers if payload_class(l.payload_type) != 'mine']
        self.mine_layers = [l for l in self.launchers if payload_class(l.payload_type) == 'mine']

    # ------------------------------------------------------------ defense

    @property
    def quadrants(self):
        return self.shields.max_strengths if self.shields else {'N': 0, 'E': 0, 'S': 0, 'W': 0}

    @property
    def shield_total(self):
        return sum(self.quadrants.values())

    @property
    def shield_spread(self):
        """How lopsided the shields are: 0 is a perfect sphere, 1 is everything on one face."""
        values = list(self.quadrants.values())
        mean = sum(values) / len(values)
        return 0.0 if mean == 0 else max(abs(v - mean) for v in values) / mean

    @property
    def boost_per_round(self):
        """Energy convertible to shield in one round: 1 point per unit, capped at 2x a quadrant."""
        surplus = self.net_energy_cruising * TICKS_PER_ROUND
        return max(0, min(surplus, max(self.quadrants.values(), default=0)))

    @property
    def ehp_facing(self):
        """Hull plus the shield you get to choose, if you can keep turning to present it."""
        return self.t.max_hull + max(self.quadrants.values(), default=0) + self.boost_per_round

    @property
    def ehp_mean(self):
        return self.t.max_hull + self.shield_total / 4 + self.boost_per_round

    @property
    def ehp_weak(self):
        return self.t.max_hull + min(self.quadrants.values(), default=0)

    @property
    def nanocyte_exposure(self):
        """Quadrants thin enough that one salvo strips them and lets nanocytes through."""
        return sum(1 for v in self.quadrants.values() if v < 100)

    # ------------------------------------------------------------ offense

    def salvo(self, target='shield'):
        """Damage put into space in one tick, everything firing at once."""
        total = 0.0
        for laser in self.lasers:
            total += laser_damage(laser) * arc_weight(laser.firing_arc)
        for launcher in self.attack_launchers:
            wh = warhead_of(launcher.payload_type)
            total += (damage_vs(wh, target)
                      * DELIVERY[payload_class(launcher.payload_type)]
                      * arc_weight(launcher.firing_arc))
        return total

    @property
    def round_throughput(self):
        """Damage over one round, capped by heat, by ammunition and by the ten ticks."""
        total = 0.0
        for laser in self.lasers:
            total += laser_shots_from_cold(laser) * laser_damage(laser) * arc_weight(laser.firing_arc)
        for launcher in self.attack_launchers:
            wh = warhead_of(launcher.payload_type)
            shots = min(launcher.initial_load, TICKS_PER_ROUND)
            total += (shots * damage_vs(wh, 'shield')
                      * DELIVERY[payload_class(launcher.payload_type)]
                      * arc_weight(launcher.firing_arc))
        return total

    @property
    def magazine(self):
        """Everything in the racks, for a game that runs long between replenishments."""
        total = 0.0
        for launcher in self.attack_launchers:
            wh = warhead_of(launcher.payload_type)
            total += launcher.initial_load * damage_vs(wh, 'shield') * DELIVERY[payload_class(launcher.payload_type)]
        return total

    @property
    def wasted_ammo(self):
        """Rounds that cannot be fired in one round because the tube can only fire once a tick."""
        return sum(max(0, l.initial_load - TICKS_PER_ROUND) for l in self.attack_launchers)

    @property
    def tubes(self):
        return len(self.attack_launchers)

    @property
    def reach(self):
        """The furthest this ship can hurt something: a laser stops where its damage does,
        a missile where its scan does, and neither can shoot what the ship cannot see."""
        laser_reach = max((l.reach for l in self.lasers), default=0)
        missile_reach = max((l.payload_type.max_scan_distance for l in self.attack_launchers), default=0)
        return max(laser_reach, missile_reach)

    @property
    def laser_share(self):
        """How much of a round's damage comes from something that never runs out."""
        total = self.round_throughput
        if not total:
            return 0.0
        laser = sum(laser_shots_from_cold(l) * laser_damage(l) * arc_weight(l.firing_arc)
                    for l in self.lasers)
        return laser / total

    @property
    def rounds_of_ammunition(self):
        """How many rounds of firing every tube the racks hold."""
        if not self.attack_launchers:
            return math.inf
        return max(l.initial_load for l in self.attack_launchers) / TICKS_PER_ROUND

    @property
    def loadout(self):
        counts = defaultdict(list)
        for l in self.launchers:
            counts[l.payload_type.name].append(l.initial_load)
        return ' '.join(f"{name}{'+'.join(str(n) for n in sorted(loads, reverse=True))}"
                        for name, loads in sorted(counts.items()))

    # ------------------------------------------------------------ economy and movement

    @property
    def cruise_drain(self):
        return self.t.max_speed // 10

    @property
    def net_energy_cruising(self):
        return self.t.generators - self.cruise_drain

    @property
    def cloak_ceiling(self):
        """The hardest this hull can cloak, which its own component works out from generators."""
        return self.cloak.max_draw_multiple * self.t.generators if self.cloak else 0

    def hiding_at(self, power: float) -> float:
        """What an enemy's scan range is multiplied by at that draw."""
        return 0.5 ** (power / self.cloak.half_power) if self.cloak else 1.0

    @property
    def free_cloak(self):
        """The draw a hull holds at cruise without spending anything it had saved."""
        return max(0, self.net_energy_cruising) if self.cloak else 0

    @property
    def ticks_at_ceiling(self):
        """How long a full battery holds the hardest cloak, cruising."""
        deficit = self.cloak_ceiling - self.net_energy_cruising
        return math.inf if deficit <= 0 else self.t.max_battery / deficit

    @property
    def mobility(self):
        """Speed, turn and throttle in one number, all three mattering."""
        return (self.t.max_speed * self.t.max_turn * self.t.max_delta_v) ** (1 / 3)

    @property
    def economy(self):
        return self.t.generators

    @property
    def scan(self):
        return self.t.max_scan_distance


# ---------------------------------------------------------------- SCORING

def normalise(profiles, metric):
    values = [metric(p) for p in profiles]
    mean = sum(values) / len(values)
    return {p.name: metric(p) / mean for p in profiles}


AXES = {
    # Offense is burst and sustain together: two tubes of five put the same damage out as one
    # tube of ten, but they put it out twice as fast, and only the salvo sees that.
    'offense': lambda p, n: math.sqrt(n['salvo'][p.name] * n['throughput'][p.name]),
    'defense': lambda p, n: n['ehp'][p.name],
    'mobility': lambda p, n: n['mobility'][p.name],
    'economy': lambda p, n: n['economy'][p.name],
}

RAW = {
    'salvo': lambda p: p.salvo(),
    'throughput': lambda p: p.round_throughput,
    'ehp': lambda p: p.ehp_facing,
    'mobility': lambda p: p.mobility,
    'economy': lambda p: p.economy,
}


def score(profiles):
    normalised = {key: normalise(profiles, metric) for key, metric in RAW.items()}
    result = dict()
    for p in profiles:
        parts = {axis: fn(p, normalised) for axis, fn in AXES.items()}
        power = 1.0
        for axis, weight in WEIGHTS.items():
            power *= parts[axis] ** weight
        result[p.name] = (power, parts)
    return result


def profile_vector(p, normalised_axes):
    """Where a ship sits in design space, for measuring how samey it is."""
    return [
        normalised_axes['offense'][p.name],
        normalised_axes['defense'][p.name],
        normalised_axes['mobility'][p.name],
        p.tubes / 3,
        p.shield_spread * 2,
        p.reach / 400,
        1.0 if p.cloak else 0.0,
        p.t.max_hull / 120,
    ]


def distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


# ---------------------------------------------------------------- REPORT

def table(rows, headers, aligns=None):
    aligns = aligns or ['<'] + ['>'] * (len(headers) - 1)
    widths = [max(len(str(r[i])) for r in [headers] + rows) for i in range(len(headers))]
    line = '  '.join(f"{h:{a}{w}}" for h, a, w in zip(headers, aligns, widths))
    print(line)
    print('  '.join('-' * w for w in widths))
    for r in rows:
        print('  '.join(f"{str(c):{a}{w}}" for c, a, w in zip(r, aligns, widths)))


def main():
    ships = [Profile(t) for t in builder.all_ship_types.values()]
    bases = [Profile(t) for t in builder.all_starbase_types.values()]

    # A hull belongs to nothing. A scenario decides which side flies it, so the grouping below is
    # a fact about the Five Faction War and not about the registry. ADR 0021.
    side = {hull: faction for faction, hulls in FACTIONS.items() for hull in hulls}
    ships.sort(key=lambda p: (side.get(p.name, ''), p.name))

    scores = score(ships)
    axes = {'offense': {p.name: scores[p.name][1]['offense'] for p in ships},
            'defense': {p.name: scores[p.name][1]['defense'] for p in ships},
            'mobility': {p.name: scores[p.name][1]['mobility'] for p in ships}}

    print("\n=== WHAT THE REGISTRY SAYS ===\n")
    table([[p.name, p.class_name, side.get(p.name, '-')[:4], p.t.max_hull,
            '/'.join(str(v) for v in p.quadrants.values()),
            p.shield_total, p.t.max_speed, p.t.max_turn, p.t.max_delta_v,
            p.t.generators, p.t.start_battery, p.scan,
            len(p.lasers), p.tubes, len(p.mine_layers),
            p.cloak.half_power if p.cloak else '-']
           for p in ships],
          ['type', 'class', 'flown by', 'hull', 'shields N/E/S/W', 'shTot', 'spd', 'trn', 'dV',
           'gen', 'batt', 'scan', 'las', 'tube', 'mine', 'halves@'])

    print("\n=== LOADOUTS ===\n")
    table([[p.name, p.class_name, side.get(p.name, '-')[:4], p.loadout,
            ' '.join(f"{l.name}({l.damage}/{l.reach})" for l in p.lasers) or '-']
           for p in ships],
          ['type', 'class', 'flown by', 'launchers', 'lasers'], ['<', '<', '<', '<', '<'])

    print("\n=== DERIVED ===\n")
    table([[p.name, p.class_name,
            round(p.salvo()), round(p.salvo('hull')), round(p.round_throughput),
            f"{p.laser_share:.0%}", round(p.magazine), p.wasted_ammo,
            f"{p.rounds_of_ammunition:.1f}", p.reach,
            round(p.ehp_facing), round(p.ehp_mean), round(p.ehp_weak),
            round(p.boost_per_round), p.nanocyte_exposure,
            p.net_energy_cruising,
            p.free_cloak if p.cloak else '-']
           for p in ships],
          ['type', 'class', 'salvo', 'vHull', 'round', 'laser%', 'magzn', 'slow', 'rnds', 'reach',
           'EHPface', 'EHPmean', 'EHPweak', 'boost', 'nanoX', 'netE', 'freeCloak'])

    print("\n=== EXCHANGE: how long you last against the average ship, over how long it lasts "
          "against you ===\n")
    print("Relative only. Nothing here models a missile's flight time or a miss, so the numbers "
          "are\ncomparable to each other and to nothing else. Above 1.00 wins the trade.\n")
    mean_ehp = sum(p.ehp_facing for p in ships) / len(ships)
    mean_out = sum(p.round_throughput for p in ships) / len(ships)
    table([[p.name, p.class_name,
            f"{(p.ehp_facing / mean_out) / (mean_ehp / p.round_throughput):.2f}"]
           for p in sorted(ships, key=lambda q: -(q.ehp_facing * q.round_throughput))],
          ['type', 'class', 'exchange'])

    print("\n=== CLOAK: what each hull can afford to hide behind ===\n")
    print("Free is the draw a hull holds at cruise off its generators alone. Ceiling is the most "
          "the\ncomponent will take. A seeker acquires at 150.\n")
    table([[p.name, p.class_name, p.cloak.half_power,
            p.free_cloak, f"{p.hiding_at(p.free_cloak):.2f}",
            round(150 * p.hiding_at(p.free_cloak)),
            p.cloak_ceiling, f"{p.hiding_at(p.cloak_ceiling):.2f}",
            round(150 * p.hiding_at(p.cloak_ceiling)),
            f"{p.ticks_at_ceiling:.0f}" if p.ticks_at_ceiling != math.inf else 'forever']
           for p in ships if p.cloak],
          ['type', 'class', 'halves@', 'free', 'x', 'seeker', 'ceiling', 'x', 'seeker',
           'ticks at ceiling'])

    print("\n=== POWER (1.00 = fleet average) ===\n")
    ranked = sorted(ships, key=lambda p: -scores[p.name][0])
    table([[p.name, p.class_name, side.get(p.name, '-')[:4], f"{scores[p.name][0]:.2f}"]
           + [f"{scores[p.name][1][a]:.2f}" for a in ('offense', 'defense', 'mobility', 'economy')]
           for p in ranked],
          ['type', 'class', 'flown by', 'POWER', 'off', 'def', 'mob', 'eco'])

    print("\n=== SAMEYNESS: nearest neighbour in design space ===\n")
    vectors = {p.name: profile_vector(p, axes) for p in ships}
    rows = []
    for p in ships:
        others = sorted(((distance(vectors[p.name], vectors[q.name]), q) for q in ships if q is not p),
                        key=lambda t: t[0])
        d, nearest = others[0]
        rows.append([p.name, p.class_name, f"{d:.2f}", f"{nearest.name} {nearest.class_name}",
                     'same line' if side.get(nearest.name) == side.get(p.name) else ''])
    rows.sort(key=lambda r: float(r[2]))
    table(rows, ['type', 'class', 'dist', 'nearest neighbour', ''])

    print("\n=== THE LINES THE FIVE FACTION WAR DEALS ===\n")
    by_side = defaultdict(list)
    for p in ships:
        by_side[side.get(p.name, 'unflown')].append(p)
    rows = []
    for faction, members in sorted(by_side.items()):
        n = len(members)
        avg = lambda f: sum(f(m) for m in members) / n
        payloads = sorted({wh.payload_type.name for m in members for wh in m.launchers})
        rows.append([faction, n, f"{avg(lambda m: scores[m.name][0]):.2f}",
                     round(avg(lambda m: m.t.max_speed)), round(avg(lambda m: m.t.max_hull)),
                     round(avg(lambda m: m.shield_total)), f"{avg(lambda m: m.tubes):.1f}",
                     f"{avg(lambda m: len(m.lasers)):.1f}",
                     f"{sum(1 for m in members if m.cloak)}/{n}",
                     ', '.join(payloads)])
    table(rows, ['faction', 'n', 'power', 'spd', 'hull', 'shTot', 'tubes', 'lasers', 'cloaked', 'payloads'])

    print("\n=== SPREAD WITHIN EACH LINE (how different its own hulls are) ===\n")
    rows = []
    for faction, members in sorted(by_side.items()):
        pairs = [distance(vectors[a.name], vectors[b.name])
                 for i, a in enumerate(members) for b in members[i + 1:]]
        cross = [distance(vectors[a.name], vectors[b.name])
                 for a in members for b in ships if side.get(b.name) != faction]
        rows.append([faction, f"{sum(pairs) / len(pairs):.2f}", f"{min(pairs):.2f}",
                     f"{sum(cross) / len(cross):.2f}"])
    table(rows, ['faction', 'internal avg', 'internal min', 'to other lines'])

    print("\n=== ARCS: how much of the fleet's firepower points everywhere ===\n")
    bearings = {0: 'forward', 45: 'fwd-stbd', 90: 'starboard', 135: 'aft-stbd',
                180: 'aft', 225: 'aft-port', 270: 'port', 315: 'fwd-port'}

    def describe(firing_arc):
        if not firing_arc:
            return 360, 'all round'
        left, right = firing_arc
        width = (right - left) % 360 or 360
        centre = (left + width / 2) % 360
        nearest = min(bearings, key=lambda b: abs((centre - b + 180) % 360 - 180))
        return width, bearings[nearest]

    def ticks_to_bear(width, max_turn):
        """Worst case ticks of turning to put a target inside the arc, at speed."""
        return math.ceil((180 - width / 2) / max_turn) if width < 360 else 0

    census = defaultdict(lambda: [0, 0.0])
    for p in ships:
        for w in p.lasers + p.attack_launchers:
            weight = (laser_shots_from_cold(w) * laser_damage(w) if w in p.lasers
                      else min(w.initial_load, TICKS_PER_ROUND)
                      * damage_vs(warhead_of(w.payload_type), 'shield')
                      * DELIVERY[payload_class(w.payload_type)])
            width, _ = describe(w.firing_arc)
            entry = census[width]
            entry[0] += 1
            entry[1] += weight
    total_weight = sum(e[1] for e in census.values())
    total_count = sum(e[0] for e in census.values())
    table([[f"{width}", f"{e[0]}", f"{e[0] / total_count:.0%}", f"{e[1] / total_weight:.0%}"]
           for width, e in sorted(census.items(), reverse=True)],
          ['arc width', 'weapons', 'share of weapons', 'share of round damage'])

    print("\nWorst case ticks of turning to bring a weapon to bear, at the arcs a redesign would "
          "use.\nAt speed 0 a ship turns any angle in one tick, so these apply only under way.\n")
    table([[p.name, p.class_name, p.t.max_turn]
           + [ticks_to_bear(w, p.t.max_turn) for w in (30, 45, 60, 90, 180)]
           for p in sorted(ships, key=lambda q: q.t.max_turn)],
          ['type', 'class', 'turn', '30', '45', '60', '90', '180'])

    print("\n=== CLOAK CURVE: what a halving power would buy ===\n")
    print("A cloak drawing `power` energy a tick, halving an enemy's scan range every "
          "`half_power`:\n  multiplier = 0.5 ** (power / half_power)\n")
    powers = (1, 2, 3, 4, 6, 8, 12, 16, 24)
    table([[f"half_power {k}"] + [f"{0.5 ** (p / k):.2f}" for p in powers]
           for k in (1, 2, 3, 4, 6, 8)],
          ['curve'] + [f"@{p}" for p in powers])

    print("\nWhat that does to the two ranges that matter, and what it costs. A guided missile "
          "acquires\nat 150; a scanning ship sees between 180 and 300. Generators run 5 to 8 a "
          "tick.\n")
    table([[p, f"{0.5 ** (p / 3):.2f}", round(150 * 0.5 ** (p / 3)),
            round(180 * 0.5 ** (p / 3)), round(300 * 0.5 ** (p / 3)),
            p * TICKS_PER_ROUND, 8 - 4 - p]
           for p in powers],
          ['power/tick', 'x', 'seeker 150', 'scan 180', 'scan 300', 'E/round',
           'net at 8 gen, speed 40'])

    print("\n=== DEAL ORDER: what the Five Faction War hands out first ===\n")
    by_type = {p.name: p for p in ships}
    rows = []
    for faction, hulls in FACTIONS.items():
        powers = [scores[h][0] for h in hulls]
        rows.append([faction, ' '.join(f"{by_type[h].class_name}({scores[h][0]:.2f})" for h in hulls),
                     f"{powers[0]:.2f}", f"{sum(powers) / len(powers):.2f}",
                     'descending' if powers == sorted(powers, reverse=True) else
                     'ASCENDING' if powers == sorted(powers) else 'unordered'])
    table(sorted(rows, key=lambda r: -float(r[2])),
          ['faction', 'deal order', 'first', 'faction avg', 'ordering'],
          ['<', '<', '>', '>', '<'])

    print("\n=== STARBASES (out of the ranking, nothing to compare them to) ===\n")
    for p in bases:
        print(f"{p.t.name}: hull {p.t.max_hull}, shields "
              f"{'/'.join(str(v) for v in p.quadrants.values())}, salvo {round(p.salvo())}, "
              f"round {round(p.round_throughput)}, gen {p.t.generators}, "
              f"boost/round {round(p.boost_per_round)}, EHP facing {round(p.ehp_facing)}")

    print("\n=== PAYLOADS ===\n")
    seen = dict()
    for p in ships + bases:
        for launcher in p.launchers:
            seen[launcher.payload_type.name] = launcher.payload_type
    table([[name, payload_class(pt), warhead_of(pt).damage, str(warhead_of(pt).damage_type),
            warhead_of(pt).range, warhead_of(pt).falloff.name,
            pt.max_speed, payload_reach(pt),
            sum(1 for p in ships for l in p.launchers if l.payload_type.name == name)]
           for name, pt in sorted(seen.items())],
          ['payload', 'kind', 'dmg', 'type', 'blast', 'falloff', 'speed', 'reach', 'tubes in fleet'])

    print("\n=== LASERS ===\n")
    table([[p.name, laser.name, laser.damage, laser.reach, laser.firing_arc or '360',
            laser_damage(laser, 0), laser_damage(laser, 10), laser_damage(laser, 20),
            laser_damage(laser, 30), laser_damage(laser, 45),
            laser_shots_from_cold(laser)]
           for p in ships for laser in p.lasers],
          ['type', 'name', 'damage', 'reach', 'arc',
           '@0', '@10', '@20', '@30', '@45', 'shots/round'])


if __name__ == '__main__':
    main()
