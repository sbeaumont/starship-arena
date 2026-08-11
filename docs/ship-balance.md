# Ship balance

What the 19 hulls and the starbase are actually worth against each other, where the variety is
thin, and which mechanics decide fights before any ship stat gets a say.

Every number here comes from [`balance.py`](balance.py) in the repository root, which reads
`builder.all_ship_types` by reflection and derives the rest. Nothing is transcribed by hand, so
the report follows the registry:

```bash
uv run python balance.py
```

Figures below were taken on 6 August 2026 and the registry has moved since, so the tables read a
few percent off a fresh run: Cairo is 1.29 rather than 1.32, Athens 0.99 rather than 1.10, Komodo
and Cobra 0.09 apart rather than 0.21. **They are regenerated with the hull pass**, which is about
to replace every number in them. Re-run `balance.py` after touching a registry file or a component,
because most of these findings move when a single constant does.

The work these findings feed into is in [plans/ship-balance-plan.md](../work/plans/ship-balance-plan.md).

## Four things the engine had wrong

The assessment was written against these, so any figure taken before them was measuring something
the game didn't do.

### The cloak had never been switched on - fixed

`ActivationCommand.execute` passed `self.selector`, the parameter object, where `Ship.activation`
expected a name string. The lookup missed and the ship recorded "Can not activate/deactivate
unknown component". `Act C1 on` parsed, validated, executed, and left the cloak off.

Every cloak in the registry was inert, which is why its energy cost never bit. The command now
reaches the component through `self.selector.value`, the way `FireCommand` does.

### Cloaking made you easier to find with a gravscan - fixed

`Gravscan.fire` passed a distance into a function that takes a scan range, so a cloak shrank the
*distance* and made its owner more likely to be picked up. Now `distance_to(ois) <=
ois.modify_scan_range(scan_distance)`, matching `Ship.can_scan`.

### A gravscan pointed forward swept only its starboard half - fixed

`fire` built the arc as `(direction - cone // 2, direction + cone // 2)` without folding it into
the circle. A 180 degree pulse straight ahead became `(-90, 90)`, and `in_firing_arc` normalises
the bearing it is given but not the arc, so every port bearing came back as 270-something and
missed. Both ends are now taken modulo 360.

### The cloak multiplier was backwards - fixed

`Cloak.modify_scan_range` returned `scan_range * (1 - strength)`, so at `strength = 0.2` a scanner
with 100 range saw you at 80. The intent was that it saw you at 20, which made every registry
value the weakest possible reading of the number written there.

The constant is gone. Strength is bought by the tick now, and the curve runs the right way by
construction. See below.

## Three mechanics decide fights, and none of them are ship stats

### Shields come back on replenish now

They didn't. A replenish refilled hull and battery and called `reset()` on every *weapon*, but
shields live in `ship.defense`, so nobody asked them. Shield strength was a one-time pool for the
whole game, which made `generators` the real long-game defensive stat.

Fixed: `Shields.reset()` restores `strengths` from `max_strengths`, and `MachineInSpace.replenish`
iterates `all_components` rather than naming a subset.

### Boost turns energy into shield at 1:1

`Shields.boost` moves battery into a quadrant point for point, capped at twice that quadrant's
maximum. Every `ShipType` shares `max_battery = 500`, so a ship that has been saving can dump 200
into one face in a single round.

The headroom is proportional to the face's own maximum. A 200-strength quadrant boosts to 400. A
50-strength quadrant boosts to 100. Extreme shield spreads amplify themselves through boost, which
is worth knowing before setting any.

### Nanocytes are all or nothing

`Shields.take_damage_from` returns 0 for a Nanocyte hit against any quadrant with strength left.
`Ship.take_damage_from` then doubles it against bare hull. 15 launchers in the fleet carry
NanoMissiles that do exactly nothing until a face is down, and up to 200 damage with a 50-unit
blast radius once it is.

Put that together with shields never regenerating and every game has a phase change in it. Nothing
lands, nothing lands, then everything lands at once.

## A laser is damage and reach

The laser was always meant to be the short-range weapon: close right in, and then it hurts more
than anything else can. `damage = strength - distance` said something else. One number was doing
two jobs, damage at point blank *and* the distance where damage ran out, so a laser could never be
brutal and short. Athens' 180 reached 180 units, further than most hulls can even scan, which made
it the longest-reaching weapon in the game.

The two numbers are separate now, and the falloff is squared:

```
damage = damage * (1 - distance / reach) ** 2, and nothing at or beyond reach
```

Squared rather than linear because orders are plotted ten ticks ahead and nobody knows where the
other ship will be when the shot goes off. A gentle curve would hand the alpha strike out for
free.

A 200 damage laser reaching 100 does 200 at contact, 162 at 10 units, 50 at half reach and nothing
at 100. Closing the last 10 units is worth as much as the 40 before it.

Every laser currently carries its old strength as `damage` and a uniform `reach` of 60, which
holds the relative ordering while the real values wait on the race work. Three families are
planned: a duellist at 250 damage to 50, a main gun at 150 to 70, and a point defence mount at 40
to 35 on a 360 arc.

That last one is why 360 arcs get to survive at all. `Missile.take_damage_from` destroys a missile
on any damage above zero, so a 40 damage laser kills a Splinter exactly as dead as a 250 one.
Stopping missiles is about coverage and rate of fire, never strength, and one Fire order per
component per tick means a ship that wants real missile defence has to carry several mounts.

`heat_per_shot` is still uniform at 20, so every laser in the game fires 8 times a round. Making
it per-laser is what would let a duellist get 5 shots and a point defence mount get 10.

**A steep curve on its own makes lasers unusable, and this has been tried before.** Orders are
plotted ten ticks ahead against a ship choosing its own course, so nobody can know they will be 15
units away on tick 7. A missile forgives a bad prediction because it steers. A laser does not, so
the weapon reads as weak when it is really unaimable, and raising the numbers to compensate is
what conflated damage with reach in the first place. Fixing the formula without fixing the aiming
walks straight back into it. The options are worked through in
[the plan](../work/plans/ship-balance-plan.md), and the front runner is a standing order that fires
whenever the target is in reach, turning a prediction into a commitment.

## Two tubes of five beat one tube of ten

Over ten ticks both put ten missiles into space, because a launcher fires once a tick at most
(`CommandSet.add` keys weapon commands by component). The difference is delivery time: five ticks
instead of ten. You concentrate on one shield quadrant before the target can turn, and you finish
before the geometry changes.

Tubes are burst. Ammunition is duration. The report scores offense as the geometric mean of
one-tick salvo and full-round throughput so both show up.

Ammunition above 10 in a single tube can't be fired within a round at all. `Rocket 20` in one tube
is the repeat offender: Lion, Cheetah and Colony each carry ten rounds they can't reach. Colony
carries 12 across its tubes.

| type | class | salvo/tick | round | magazine | unreachable in a round |
|---|---|---|---|---|---|
| H2545 | Cairo | 423 | 2642 | 1750 | 0 |
| A2545 | Terrapin | 317 | 2019 | 2250 | 4 |
| H2527 | Athens | 285 | 2280 | 360 | 0 |
| I2526 | Colony | 281 | 1895 | 2250 | 12 |
| F2533 | Lion | 147 | 674 | 975 | 10 |
| F2534 | Cheetah | 138 | 920 | 825 | 10 |

## Sameyness, with counts

- **All 19 hulls carry Rockets.** 28 tubes across the fleet.
- **17 of 19 carry exactly 10 mines.** Sixteen have the identical
  `Launcher('M1', SplinterMine(), 10)`; Babylon swaps in a NanocyteMine, also 10. Only Athens and
  Rome go without.
- **All 20 objects carry an identical `Gravscan('G')`.**
- **Every payload but the EMPMissile is the same airframe**: speed 60, battery 75,
  `energy_per_move` 5, scan cone 45, scan range 150. Only the warhead differs. There is no
  fast-interceptor versus long-loiter axis anywhere in the game.
- **Every laser shares heat and energy behaviour.** Only strength varies.
- **Shields are flat almost everywhere.** Colony's 260/125/50/125 is the only real asymmetry;
  next most lopsided is Cairo's 150/100/130/100.
- **Every cloak is 0.20 or 0.25 at 5 energy a tick.** Tiger's 4 is the sole exception.

Nearest-neighbour distance in profile space finds the redundancies:

```
R2545 Komodo  0.21  R2551 Cobra    same race
R2551 Cobra   0.21  R2545 Komodo   same race
F2533 Lion    0.33  F2547 Panther  same race
A2553 Frog    0.38  F2547 Panther
```

Komodo and Cobra share speed, turn, delta-v, battery, generators, scan range and shields exactly.
They differ in hull (110 against 105), laser (130 against 80) and splinter arrangement (one tube of
10 against two of 4). Cobra's only advantage is splinter burst; everything else about it is worse.
It's the clearest candidate for deletion or a redesign.

Worth keeping: **Terrapin, Rome and Dragon carry no laser at all.** That reads instantly at the
table, and Rome with forty Splinters really is a different ship from Athens with two 180-lasers and
sixteen rockets.

## Two thirds of the fleet's firepower points everywhere

```
arc width  weapons  share of weapons  share of round damage
360             65               66%                    64%
180             15               15%                    21%
90              18               18%                    16%
```

Three widths in the whole registry. This is the largest single source of variety going unused, and
narrowing arcs turns `max_turn` into a stat that decides fights. Worst case ticks of turning to
bring a weapon to bear, under way:

| type | class | turn | 30° | 45° | 60° | 90° | 180° |
|---|---|---|---|---|---|---|---|
| I2552 | Swarm | 20 | 9 | 8 | 8 | 7 | 5 |
| I2544 | Hive | 25 | 7 | 7 | 6 | 6 | 4 |
| H2545 | Cairo | 35 | 5 | 5 | 5 | 4 | 3 |
| F2551 | Tiger | 50 | 4 | 4 | 3 | 3 | 2 |

One thing still gets in the way of narrowing them.

**The NPC gunner doesn't check arcs.** `Laser.can_fire_at` tests heat, energy, scan and damage but
not `in_firing_arc`, so `Gunner.decide` queues shots that `Laser.fire` then refuses. Invisible
today because almost every laser is 360.

A stationary ship used to turn any angle in one tick, because `Ship.turn` applied `max_turn` only
when `speed > 0`, and sitting still is the cheapest thing a ship can do. Every arc was a 360 arc
if you were willing to park. The exemption is gone; a turn beyond `max_turn` is clamped and the
player is told, the way an over-range acceleration already was.

## The cloak is bought by the tick

A fixed strength gave 36 to 68 units of concealment for 5 energy a tick, which was the entire
generator output of most hulls and 50 shield points a round given up through boost. Every cloaked
ship ran an energy deficit at cruise for almost nothing. Read the other way, where 0.2 means "seen
at 20% of range", the same values were a problem in the opposite direction: Rome would have been
seen at 60 instead of 300.

A cloak drawing `power` energy a tick, halving an enemy's scan range every `half_power`, handles
both:

```
multiplier = 0.5 ** (power / half_power)
```

`power = 0` is off and costs nothing, so there is no on/off state to keep. The draw is capped at
twice what the hull generates, which is where the curve has flattened anyway. Ordering it pays for
the tick it lands in, because scans are read after the move; raising it pays only the increase.

Every hull is on `half_power = 4` for now. What each race should get is part of the arcs
conversation, since it's the same question about what a race feels like.

| type | class | free | x | seeker | ceiling | x | seeker | ticks at ceiling |
|---|---|---|---|---|---|---|---|---|
| H2527 | Athens | 4 | 0.50 | 75 | 16 | 0.06 | 9 | 42 |
| F2551 | Tiger | 3 | 0.59 | 89 | 16 | 0.06 | 9 | 38 |
| A2539 | Caiman | 3 | 0.59 | 89 | 14 | 0.09 | 13 | 45 |
| H2535 | Rome | 2 | 0.71 | 106 | 10 | 0.18 | 27 | 62 |
| R2531 | Dragon | 2 | 0.71 | 106 | 10 | 0.18 | 27 | 62 |

Free is what a hull holds at cruise off its generators alone, ceiling is the most the component
takes, and seeker is where a guided missile acquires instead of 150. So a cloak running for free
is a modest permanent advantage, and disappearing properly is a burst of 4 to 6 rounds that stops
you boosting shields while it lasts.

`balance.py` prints the curve for `half_power` 1 through 8. At 1 the choice is trivial, because 3
energy is near invisibility. At 8 it is never worth buying, because 8 energy only halves you.

## The gravscan now has to be pointed

It exists so teams stop hunting each other in the dark, which is the right call. The numbers just
didn't make the search directed. Reach fell linearly from 3000 at a 30 degree cone to 300 at 360,
so two 180 degree pulses cost 20 energy and covered everything out to 1773, against a passive scan
of 180 to 300. There was no reason to ever point it anywhere in particular. It also reached 10 to
16 times further than any passive scanner, which left `max_scan_distance` nearly meaningless as a
ship stat.

Reach now holds the swept area constant. A pulse has a fixed amount of energy to spread over the
cone it covers, so twice the width reaches `1/sqrt(2)` as far:

```
reach = max_scan_distance * sqrt(30 / cone)
```

Anchored at `max_scan(200)`, which is 1200 for the narrowest pulse the order accepts:

| cone | 30° | 60° | 90° | 180° | 360° |
|---|---|---|---|---|---|
| was | 3000 | 2755 | 2509 | 1773 | 300 |
| now | 1200 | 848 | 692 | 489 | 346 |

Looking everywhere at once is now barely better than a passive scanner. A needle sees four times
as far as one, and covering the whole circle in 30 degree pulses costs 120 energy against 10 for
a single sweep, so the choice of where to look is a real one.

## Race identity

| race | n | power | spd | hull | shTot | tubes | lasers | cloaked | exclusive payloads |
|---|---|---|---|---|---|---|---|---|---|
| insectoid | 3 | 1.12 | 28 | 160 | 577 | 5.7 | 1.0 | 0/3 | none |
| human | 4 | 1.11 | 40 | 115 | 458 | 3.5 | 1.0 | 3/4 | EMPMissile, NanocyteMine |
| amphibian | 4 | 0.98 | 42 | 108 | 410 | 4.8 | 1.0 | 2/4 | PowerSplinter |
| reptilian | 4 | 0.88 | 35 | 111 | 430 | 4.0 | 0.8 | 2/4 | none |
| feline | 4 | 0.84 | 50 | 80 | 405 | 3.2 | 1.2 | 4/4 | none |

**Insectoid** and **Feline** are real identities, and they're opposites. Slow fat many-tubed
fortresses with no cloak on any hull, against fast thin few-tubed raiders with cloak on all four.
Both read instantly. The Feline identity costs more than it pays, though: 0.84 against 1.12.

**Human** is the best defined in play terms. Exclusive EMP and Nanocyte mines, the only
180-strength lasers, and the widest internal spread of any faction at 1.30.

**Amphibian** has one distinguishing feature, PowerSplinter, and it's "Splinter but 100 instead of
75". Middle of the road on every other axis.

**Reptilian has nothing exclusive at all.** Same payload set as Feline and Insectoid, middling
stats, and it holds the fleet's duplicate pair. It's the one faction with no answer to "why would I
fly these?"

## Power levels

```
type   class      race   POWER   off   def   mob   eco      exchange
H2545  Cairo      huma    1.32  1.70  1.09  1.13  1.20          1.76
I2526  Colony     inse    1.21  1.17  1.66  0.79  0.90          1.91
I2552  Swarm      inse    1.13  1.27  1.43  0.57  0.90          2.01
H2527  Athens     huma    1.10  1.29  0.90  1.09  1.20          1.25
A2545  Terrapin   amph    1.07  1.29  1.02  0.96  0.75          1.25
H2535  Rome       huma    1.05  1.29  1.02  0.79  0.75          1.58
A2539  Caiman     amph    1.02  1.12  0.87  1.13  1.05          0.89
F2551  Tiger      feli    1.01  1.05  0.81  1.40  1.20          0.93
I2544  Hive       inse    1.01  0.99  1.21  0.74  0.90          1.10
H2552  Babylon    huma    0.96  0.83  1.09  1.01  1.05          1.03
R2545  Komodo     rept    0.94  0.90  1.02  0.83  1.05          1.03
A2527  Alligator  amph    0.94  0.92  0.87  1.13  1.05          0.80
R2531  Dragon     rept    0.93  0.93  1.09  0.74  0.75          0.90
A2553  Frog       amph    0.90  0.99  0.75  1.05  0.90          0.70
F2547  Panther    feli    0.87  0.73  0.83  1.27  1.20          0.60
R2551  Cobra      rept    0.85  0.70  1.00  0.83  1.05          0.60
R2525  Viper      rept    0.79  0.66  0.79  1.01  1.05          0.52
F2534  Cheetah    feli    0.79  0.57  0.77  1.44  1.20          0.43
F2533  Lion       feli    0.70  0.51  0.79  1.09  0.90          0.32
```

1.00 is the fleet average on every column. The spread is 1.9x top to bottom.

**Cairo is the outlier upward.** A 180-laser, four attack tubes, the best shields in the human
line, 8 generators and 45 speed. It has no weakness at all. Either the 180 laser, which should be
Athens' signature, or a tube has to go.

**Lion is the outlier downward.** A laser that does nothing past 50 units, splinter loads of 4 and
3, and half its rocket magazine out of reach within a round. Offense index 0.51.

The exchange column punishes the Felines harder than the power score does, because thin hulls
compound: they die fast and shoot little. Speed doesn't appear in that column at all, which is fair
warning that both numbers under-rate mobility. If Feline speed is meant to be worth something, it
has to turn into damage or survival through a mechanic that doesn't exist yet. A to-hit penalty, a
missile that can't turn tight enough, something.

## Deal order in the Five Faction War

`FiveFactionWar._faction_records` deals the hulls round robin, so the list order in
`arena/app/scenarios/five_faction_war.py` decides who gets what first.

| faction | deal order | first | avg | ordering |
|---|---|---|---|---|
| Human | Cairo(1.32) Babylon(0.96) Rome(1.05) Athens(1.10) | 1.32 | 1.11 | unordered |
| Feline | Tiger(1.01) Panther(0.87) Cheetah(0.79) Lion(0.70) | 1.01 | 0.84 | descending |
| Insectoid | Hive(1.01) Swarm(1.13) Colony(1.21) | 1.01 | 1.12 | **ascending** |
| Amphibian | Alligator(0.94) Caiman(1.02) Terrapin(1.07) Frog(0.90) | 0.94 | 0.98 | unordered |
| Reptilian | Komodo(0.94) Viper(0.79) Dragon(0.93) Cobra(0.85) | 0.94 | 0.88 | unordered |

Feline is the only faction ordered by strength. Insectoid is ordered backwards, so its best hull
goes to whoever registers third. And the first ship dealt ranges from 0.94 to 1.32 depending on
faction, which is the accident the TODO entry was written to prevent.

## Method

Everything is read by reflection from `builder.all_ship_types` and the component classes.

| metric | how |
|---|---|
| salvo | one tick, everything firing. Lasers give `damage x (1 - LASER_RANGE/reach)^2`; launchers give `warhead damage x delivery x arc weight` |
| round throughput | ten ticks. Lasers capped by simulating the heat loop (8 shots from cold), launchers by `min(ammo, 10)` |
| magazine | the whole racks, for a game that runs long between replenishments |
| EHP facing / mean / weak | `hull + quadrant + boost_per_round`, for the best, average and worst quadrant |
| boost per round | net energy x 10, capped at the quadrant maximum, which is the headroom the 2x cap gives |
| net energy | `generators - max_speed//10`, minus the cloak |
| mobility | cube root of `speed x turn x delta_v`, so all three have to be present |
| reach | `min(laser strength, scan)`, or missile acquisition range |

The judgement calls sit in one block at the top of `balance.py`:

- **`LASER_RANGE = 20`.** The range a laser is assumed to be used at, and the biggest lever by far.
  Damage falls off squared to nothing at `reach`, so a laser scored at the range missiles cross
  reads as worthless. Missiles are scored at contact, so the two weapon classes are each judged in
  their own band. Worth sweeping.
- **`DELIVERY = {guided: 1.0, dumb: 0.45, mine: 0.0}`.** How much of a payload lands. Mines are
  area denial and get counted separately rather than as offense.
- **`ARC_FLOOR = 0.55`.** A 90-degree weapon is worth `0.55 + 0.45 x (arc/360)` of a turret, since
  you can point the ship.
- **Damage types.** Nanocytes count 0 against shields and 2x against hull; EMP counts 2x against
  shields and 0 against hull. Hence the separate `vHull` salvo column, and why Cairo reads 423
  shielded but 223 against bare hull while Hive reads 254 and 454.
- **`WEIGHTS`**: offense .40, defense .35, mobility .15, economy .10, combined as a weighted
  *geometric* mean of fleet-relative values, so a zero on one axis can't be bought off with
  another. Offense is itself `sqrt(salvo x throughput)`, which is where the two-tubes-of-five
  effect lives.

Sameyness is Euclidean distance over an 8-dimensional normalised profile: offense, defense,
mobility, tube count, shield spread, reach, cloak, hull.

### What it doesn't model

No positioning, no missile flight time, no interception, no point defense, no fog of war, and
nothing about the `Pilot` and `Gunner` controllers. It ranks hulls. Simulating a fight is a
different job.

The exchange column is relative only. Its absolute values mean nothing, because a launcher that
fires every tick and always hits is a fiction.

If the next step is a real duel simulator, missile flight time and lasers shooting down incoming
are the two to start with. Those are exactly what make the launcher numbers here optimistic and
the laser numbers pessimistic.