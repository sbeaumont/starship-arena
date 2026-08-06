# Making the ships feel different

The assessment is in [docs/ship-balance.md](../docs/ship-balance.md). This file is the order the
work goes in, and the things that will bite.

Most of it is engine work that has to land before any registry values are worth arguing about.
Four bugs were hiding what the numbers do, so tuning against them would have been tuning against a
fiction. Three are fixed. The registry rewrite is last and is blocked on a design conversation,
not on code.

## What exists to build on

`Component` already carries the whole vocabulary a machine uses to talk to its parts, with neutral
defaults that components shadow. `reset`, `use_energy`, `activation` and `modify_scan_range` are
all there. Nothing below needs a new question asked of every component.

`Starbase.replenish` is the one caller of `reset()`, and it now asks `all_components` rather than
naming `weapons`.

`FireCommand.execute` is the pattern the other component commands should follow: it resolves the
component through `self.selector.value` and calls it directly, never routing back through the ship.

`Ship.accelerate` is the precedent for a limit: clamp, then record an `InternalEvent` saying what
was done. Turning already does the same thing, just with an exemption in front of it.

`balance.py` at the repository root reads the registry by reflection and prints the tables the
assessment is built from. Every step below that changes a number should be followed by a run of
it.

---

## Step 1: shields come back on replenish - done

`Shields.reset()` restores `strengths` from `max_strengths`, and `Starbase.replenish` iterates
`all_components` instead of `ship.weapons`. Shields live in `defense`, which is why they were
never asked.

217 tests pass. One behaviour change worth knowing: replenishing mid-round while a quadrant sits
boosted above its maximum now pulls it back down. `post_round_reset` already does that at the end
of a round, so the two agree.

`reset` is a poor name next to `round_reset` and `post_round_reset`, and that ambiguity is
probably why shields were missed. Renaming it to something that says "restore to factory
condition" would be a separate, mechanical change.

## Step 2: the activation command reaches its component - done

`ActivationCommand.execute` passed `self.selector`, the parameter object, where `Ship.activation`
expected a name string. The lookup missed, the ship recorded "Can not activate/deactivate unknown
component", and the order did nothing. **No cloak in this game had ever been switched on.**

It now reaches the component the way `FireCommand` does:

```python
self.selector.value.activation(self.params['on/off'].value)
```

The selector proves the component exists during validation, so the guard inside `Ship.activation`
was re-checking something ADR 0005 had already settled.

`test/engine/test_commands.py` covers the path that had no coverage at all, which is how this
survived: switching on, switching off again, paying for the tick it happens on, an unknown
component, and a component whose parameters are not an on/off.

## Step 3: `Ship.fire` and `Ship.activation` go, with the protocol - done

Both were dead once step 2 landed. `Ship.fire` already was: `FireCommand` calls `weapon.fire(...)`
on the component and never touched the ship.

They could not be deleted on their own. `Commandable` is a `@runtime_checkable` Protocol and
`isinstance(ois, Commandable)` gates order execution in `round.py` and `game.py`, so removing the
methods without the protocol entries would have left every ship silently taking no orders. Both
went in one change, along with the now-unused `ObjectInSpace` import in `command.py`.

Verified rather than assumed, because this fails by doing nothing: ships and starbases still
answer `True`, rockets, splinters and mines still answer `False`. `commands` is what keeps those
out, and it is untouched.

## Step 4: turning is limited whatever the speed - done

`Ship.turn` applied `max_turn` only when `speed > 0`, and `TurnParameter` said so out loud:
"outside max turn, but possible at speed 0". A stationary ship turned 180 degrees in one tick, and
sitting still is also the cheapest thing a ship can do, because movement costs `speed // 10`. Any
firing arc narrower than 360 was defeated by stopping and pivoting, which would have made step 7
pointless.

The `speed > 0` condition is gone and the feedback now says what will happen: limited to
`|max_turn|`. The clamp and the `InternalEvent` stay, so an over-range turn is honoured as far as
it can be rather than refused outright. That matters for `Pilot`, which asks for the whole bearing
to its target and would otherwise never turn at all.

Low risk, because the game UI already clamps plotted turns to `±max_turn`
(`game-ui/src/lib/FactionMap.svelte:699`). Only a hand-written command file could reach the
exemption.

## Step 5: the cloak draws the power it is given - done

Two separate problems. The multiplier was backwards from intent, and the strength was a constant
when it should be bought.

`Cloak.modify_scan_range` returned `scan_range * (1 - strength)`, so `strength = 0.2` meant a
scanner with 100 range saw you at 80. The intent was that it saw you at 20. Every registry value
was therefore the weakest possible reading of the number written there.

Replacing the constant with a curve fixed the direction and the scaling together:

```python
def modify_scan_range(self, scan_range: float) -> float:
    return round(scan_range * 0.5 ** (self.power / self.half_power), 1)
```

`half_power` is the energy a tick that halves an enemy's scan range; `power` is what the player is
spending. `power = 0` is off and free, so the on/off state disappears into the number and nothing
needs an `active` flag. The battery does the bounding, so there is no clamp to write.

`half_power = 3` puts the useful range where the economy already is:

| power/tick | multiplier | seeker 150 | scan 180 | scan 300 | E/round | net at 8 gen, speed 40 |
|---|---|---|---|---|---|---|
| 1 | 0.79 | 119 | 143 | 238 | 10 | 3 |
| 2 | 0.63 | 94 | 113 | 189 | 20 | 2 |
| 3 | 0.50 | 75 | 90 | 150 | 30 | 1 |
| 4 | 0.40 | 60 | 71 | 119 | 40 | 0 |
| 6 | 0.25 | 38 | 45 | 75 | 60 | -2 |
| 8 | 0.16 | 24 | 28 | 47 | 80 | -4 |
| 12 | 0.06 | 9 | 11 | 19 | 120 | -8 |

`half_power = 1` is too steep: 3 energy is near invisibility. `half_power = 8` is too shallow: 8
energy only halves you. Every hull is on 4 for now, which keeps cloaks as undifferentiated as they
already were. What each race gets is part of step 7, because it is the same question about what a
race feels like, and `balance.py` prints the whole grid so other values can be looked at rather
than guessed.

The draw is capped at twice what the hull generates, which is 10 to 16 across the fleet. A ceiling
of `max_battery` would have offered a slider running to 500 for a curve that has flattened by 12,
and tying it to generators means a hull with big engines genuinely cloaks harder.

### Power is a setting, Boost is an act

`activation(on_off: bool)` stays as it is. A cloak wants a number, and the two commands that spend
energy now say which kind of spending they are:

- **`Boost`** hands over energy once. It leaves the battery immediately, the shield keeps it for
  the round, and `post_round_reset` dissipates it.
- **`Power`** sets a draw that holds until changed. The component takes it every tick in
  `use_energy()` until told otherwise.

A player reading their own orders can tell which one keeps costing without looking anything up.

`PowerCommand` is a `ComponentCommand` resolving through `self.selector.value` the way
`FireCommand` does, with `NumberInRangeParameter` for the amount, and `power_up` joins the
`Component` vocabulary next to `activation` with the same shape of neutral default. `Cloak` returns
the power parameter from `expected_parameters` instead of `OnOffParameter`, so `Act C1 on` is now
refused at validation and `Power C1 4` is not.

Two ordering details, both handled:

`do_tick` calls `use_energy()` before `pre_move_commands`, so a draw ordered this tick would not
be charged until the next one, while `modify_scan_range` is read during the scan phase after the
move and does hide the ship this tick. `power_up` therefore charges the increase on the spot.
Charging the whole new level would have double-billed what `use_energy` already took, and charging
nothing would have sold one tick of deep cloak for free.

When the battery cannot cover the draw, the cloak shuts down and records an `InternalEvent`, which
is what `Ship.use_energy` already does with speed.

`OnOffParameter` and `ActivationCommand` now have no component using them. Kept, as agreed, for
whatever wants switching rather than setting.

Still open: the game UI has no control for either command. `Parameter.kind` already distinguishes
them (`shield_boost`, `on_off`, `number_in_range`), and `_weapon_info` already passes a range
through for the gravscan's cone, so a power slider is the same machinery pointed at `ecm` instead
of `weapons`.

## Step 6: the gravscan has to be pointed - done

Three things, two of them bugs.

**A cloak made its owner easier to find.** `fire` passed a distance into `modify_scan_range`,
which takes a scan range. For a cloaked target that returned a *smaller* number, which is more
likely to pass the comparison. Now `distance_to(ois) <= ois.modify_scan_range(scan_distance)`,
matching `Ship.can_scan`.

**A pulse straddling the bow swept only its starboard half.** The arc was built as
`(direction - cone // 2, direction + cone // 2)` with no fold into the circle, so 180 degrees
straight ahead became `(-90, 90)`. `in_firing_arc` normalises the bearing it is given but not the
arc, so every port bearing arrived as 270-something and missed. Both ends are now taken modulo
360, and `(270, 90)` wraps the way every other arc does.

**Reach now holds the swept area constant.** A pulse has a fixed amount of energy to spread over
the cone it covers, so twice the width reaches `1/sqrt(2)` as far:

```python
reach = max_scan_distance * sqrt(narrowest_cone / scan_cone)
```

Anchored at `max_scan(200)`. `narrowest_cone` is the same 30 the order's parameter already
enforces, so the two cannot drift apart. `min_scan_distance` is gone, along with
`default_scan_cone` and `active`, which nothing read.

| cone | 30° | 60° | 90° | 180° | 360° |
|---|---|---|---|---|---|
| was | 3000 | 2755 | 2509 | 1773 | 300 |
| now | 1200 | 848 | 692 | 489 | 346 |

Looking everywhere at once is now barely better than a passive scanner at 180 to 300. Covering the
whole circle in 30 degree pulses reaches 1200 but costs 120 energy against 10 for one wide sweep,
so where to look is a real choice. Scaling energy with the cone was the other lever considered and
is not needed: the reach curve already makes the lazy option worthless.

## Step 7: arcs, and the registry rewrite - blocked

Two thirds of the fleet's weapons and 64% of its round damage sit on 360 degree arcs, and the
whole registry uses only three widths: 360, 180 and 90. Narrowing them is the single largest
source of variety available, and it turns `max_turn` into a stat that decides fights: worst case
turning to bring a 30 degree arc to bear is 9 ticks for a Swarm and 4 for a Tiger.

Two things to settle before writing any of it.

**An `arc()` helper belongs in the engine, not in `balance.py`.** The case for it is reading, not
safety: players get sliders and the code constrains them, so nobody can transpose anything. But
`(0, 180)` and `(180, 0)` are starboard and port, and neither tuple says so. Somebody writing forty
of these by hand has to work each one out from `in_firing_arc` every time. Next to it in
`weapon.py`:

```python
def arc(centre: int, width: int) -> tuple:
    """A firing arc that wide, centred that many degrees off the bow."""
    return (centre - width // 2) % 360, (centre + width // 2) % 360
```

Then the registry reads `arc(0, 30)`, `arc(90, 60)` for a starboard broadside, `arc(180, 90)` for
a stern chaser. `balance.py` already reports the census and needs nothing.

**The NPC gunner does not check arcs.** `Laser.can_fire_at` tests heat, energy, scan and damage
but not `in_firing_arc`, so `Gunner.decide` queues shots that `Laser.fire` then refuses. Invisible
today because almost every laser is 360; it becomes noisy the moment arcs narrow.

### What each race is for

Settled in conversation. The values are not, but the direction is.

**Reptilian: the ambush.** The strongest cloak in the game and lasers as the alpha strike. Creep
in unseen, and at knife range a laser hurts more than anything else can. Cold, patient, one
strike. No mines: that is the thing that finally makes them not a Feline. Cloak `half_power` 3.

**Feline: the raider.** Fast, thin, agile, and stealthy but less so than the snake. Their speed
pays through arcs, because turn rate decides who brings guns to bear and they reach a 30 degree
arc in 4 ticks where a Swarm needs 9. They carry a few mines to place where you will be, which is
a different job from laying a field. Cloak `half_power` 6, so at the same draw they sit at 0.50
where a Reptilian sits at 0.25.

**Insectoid: the swarm and the fortress.** Turning at 20 to 30 they cannot have narrow arcs at
all, so their identity is broadsides, mines laid to deny ground, and enough shield and generator
to hold it. Fields, not placements.

**Human: attrition.** They already own EMP and nanocyte mines exclusively, which is the kit for
taking something apart rather than killing it. Plays directly into the phase change: strip a face,
then convert.

**Amphibian: standoff.** PowerSplinter becomes the start of a longer-reaching family rather than
a bigger number. This is the niche that most needs the payload airframe to vary, because every
missile in the game currently dies at 900 units.

Every hull keeps a mine tube and a rocket tube. They are the flattest thing in the registry, 17 of
19 carrying exactly 10 mines and all 19 carrying rockets, and the variety has to come from
somewhere else. Losing its only area denial and its only dumb-fire weapon costs a hull more than
the sameyness costs the fleet.

### The three laser families

The rework in step 8 makes these expressible. Damage and reach are separate numbers now, so a
laser can be brutal and short, which it could not be before.

| role | damage | reach | arc | feel |
|---|---|---|---|---|
| duellist | 250 | 50 | 30 forward | one pass, one decision |
| main | 150 | 70 | 60 | the standard hammer |
| point defence | 40 | 35 | 360 | kills what is incoming |

Point defence is the answer to "should 360 arcs survive". `Missile.take_damage_from` destroys a
missile on any damage above zero, so a 40 damage laser kills a Splinter exactly as dead as a 250
one. Anti-missile work is about coverage and rate, never strength. One Fire order per component
per tick means a ship that wants real missile defence carries several mounts, which is a genuine
loadout decision, and it gives `Gunner` a job worth doing. A few defence-oriented hulls get them.

`heat_per_shot` is still a class attribute, so every laser fires 8 times a round. Making it a
constructor argument is what lets a duellist get 5 shots and a point defence mount get 10.

## Step 8: a laser is damage and reach, falling off squared - done

`strength` did two jobs: damage at point blank and the range where damage reached zero. So a laser
could not be short and hard, and Athens' 180 reached 180 units, further than most hulls can scan.
The intent was always the opposite, the weapon you close to knife range to use.

```
damage = damage * (1 - distance / reach) ** 2, and nothing at or beyond reach
```

Squared rather than linear because orders are plotted ten ticks ahead and nobody knows where the
other ship will be. A forgiving curve would hand out the alpha strike for free; a squared one
means closing is a real gamble.

Past `reach` the square climbs again, so out of range is answered before the formula is used.
There is a test for it.

Every laser is on `reach = 60` with its old strength as `damage`, which keeps the relative
ordering exactly as it was and leaves the real values to the families above. The starbase's two
300 lasers are on 60 as well, which suits a fortress badly and wants revisiting with the rest.

`balance.py` scores lasers at 20 units now rather than 60. Squared falloff to a 60 reach means a
laser judged at the range missiles cross reads as worthless, so the two weapon classes are each
scored in their own band. `LASER_RANGE` is the constant.

`test_ship_spawner` had the old arithmetic written into its setup: Voyager 20 off the base, one
300 laser doing 280. It now does 133, so the base fires both of its lasers to make the kill.

## Designing a short-range weapon so it feels good

This has been tried before. Steep falloff made lasers weak, and the fix was to raise strength,
which is how one number came to mean both damage and reach. Step 8 has re-created the original
condition, so the curve on its own will fail the same way unless something else changes with it.

**The problem is not the damage, it is the aiming.** Orders are plotted ten ticks ahead, both
ships move, and a laser does not chase. A missile forgives a bad prediction because it steers; a
laser asks you to know, at writing time, that you will be 15 units away on tick 7 from a ship
whose captain is deciding their own course at the same moment. Nobody can know that. So the
weapon is not weak, it is unaimable, and any falloff steep enough to be exciting makes it worse.

What a mistimed shot costs today, which is less than it looks:

- Out of arc, or visible but out of reach: `Laser.fire` returns before heat and energy are spent.
  Free.
- Fired at something the ship cannot see: falls through to the failure branch and spends the full
  shot anyway.

So the real price of a bad prediction is the order slot and the tick, not the battery. Making
misses cheaper is not the lever; there is almost nothing left to give back.

**The principle: a short-range weapon has to turn a prediction into a commitment.** A player
should be able to say "when I am close enough, hit them" instead of "on tick 7 I will be close
enough". Then the interesting decision becomes whether to commit to the approach at all, which is
a decision worth making, rather than arithmetic about where two ships will be, which is not.

Options, in the order I would try them.

**A standing engage order.** `Engage L1 <target>` holds until changed and fires on every tick the
target is in reach and in arc. Heat caps it at 8 shots a round on its own, so it needs no further
limit. This fits the vocabulary already built: Boost is an act, Power is a setting, Engage is a
standing order.

It also already exists in another form. `Gunner.decide` is exactly this mechanism for NPC hulls:
it looks for something `laser.can_fire_at` and queues a shot. One wrinkle worth copying carefully
rather than copying blindly, though: `Gunner` queues for `tick.tick + 1` off this tick's geometry,
which builds in a tick of lag. At a reach of 50 and a closing speed of 90 the range has changed by
more than the reach in that time. A player-facing engage order should resolve in the tick it fires.

This is the one that makes narrow arcs interesting instead of punishing, because the game becomes
about holding a bearing rather than predicting a tick.

**An inner plateau on the falloff.** Full damage inside some radius, then squared away to reach.
"Close enough" becomes a band rather than a point, and the reward for a good approach stops being
all-or-nothing. Cheap to do and composes with the engage order.

**Nothing else.** Making misses cheaper is already nearly true, and giving laser hulls more speed
and turn treats the symptom.

Until this is settled the laser families in step 7 are guesses, because how hard a laser hits can
only be judged once it is known how often it gets to hit at all. Whatever is chosen wants an ADR:
it is a decision about how the game is played, not a number.

## A disabling hit, and what point defence is for

Three kinds of claim below, kept apart because they need different amounts of trust. **Decided** is
what came out of the design conversation. **Derived** is arithmetic anyone can check. **Proposed**
is where I think code goes, and that is the part to argue with.

### The mechanic - decided

A hit either takes something apart or stops it working, and those are different things.

A **disabling hit** stops a thing functioning. A missile or mine that takes one goes inert and
**disappears**, warhead unfired: clutter on the map costs more than the fog of war a drifting hulk
would buy. A ship that takes one loses a component for a while, which is the existing
"damage to individual components" backlog item arriving through the front door. EMP is already a
blunt version, since a drained battery means no lasers, no cloak and a forced slowdown.

So point defence is not a weak laser. It is a different weapon: it does not blow a missile up, it
fries the seeker. Damage and disabling become two things a weapon can do rather than two points on
one scale, and a ship cannot repurpose its defensive mounts into an alpha strike.

### Why point defence needs it - derived

Landing a hit and resolving a kill are separate, and both are deliberate. Hits land as they happen
and are simultaneous; the destroyed are cleared only when the tick ends. Two gunners can overkill
one missile and neither wasted the shot.

Which means **shooting a missile in the tick it detonates does not stop it detonating.** Both land.

Without disabling, an interception has to happen the tick before, and that sets a floor under how
far a point defence mount must reach. A missile detonates during a move whose leg passes within its
blast radius, so from a distance `D` it goes off if `D - speed <= blast`. Working back to where it
sits at decide time while still alive:

| what | approach | last live distance |
|---|---|---|
| Rocket, speed 60, blast 20 | flying straight past | 80 |
| Splinter, speed 60, blast 6 | dumb approach | 66 |
| Splinter, decelerating onto you | `_intercept` sets speed to `distance - 1` | ~40 |

A 35-reach mount would never see a live missile. Not rarely: never. So without disabling the
defensive laser has to be the *longest* one on the ship, which is a strange shape for a weapon
whose job is close-in work.

With disabling, the floor disappears. The mount catches the missile at the moment it would go off,
at 8 units or 40, and can be short and cheap again.

### What it costs - decided, and not free

Detonation would have to leave `decide` for a resolution step, so that a disabling hit declared in
the same tick can win. That is the split deliberately *not* made so far.

And the chain-detonation branch depends on damage landing inside `decide`:

```python
elif self.container.is_destroyed:
    # Whatever killed it set it off, which is what makes one blast carry to the next.
    self.explode(world)
```

A resolution step would have to loop until nothing new goes off, or chains stop at one link.

### Where it lives - decided

**A component carries a set of `status_effects`.** `DISABLED` is the first of them. On `Component`
rather than on the object, so parts can be knocked out one at a time. It mirrors
`ObjectInSpace.tags`, which is the same idea one level up and is what the spawner's `CLAIMED`
already uses: a marker that is there or is not, with nothing read off it.

The word is not `conditions`. `TickCondition` already means a ship's readouts tick by tick, and the
game UI renders it as `hull 90 · bat 40`, so the two would collide in the layer players read.
`status_effects` is wordier and says which one it is.

**No duration.** A set, not a countdown. Everything that needs one is later work, and the first
will be EMP disabling a ship's components for a few ticks rather than only draining its battery.
That is the point at which `information.md`'s rule bites: a duration is a value, and the moment a
marker carries a value it stops being a marker and becomes instance state with a name. A dict
keyed by effect, and something has to tick it down.

**`is_destroyed` stays derived.** A disabling kill sets hull to 0 like any other, so deadness is
still worked out from hull and needs no state of its own. A `DEAD` status effect would read
consistently beside `DISABLED`, which is the argument for it, and it also lands on
`information.md`'s first rung and its named anti-pattern, two facts about one thing that can
disagree. Left out for now, worth revisiting once there are more effects to be consistent with.

**The two-pass shape already exists and is already justified.** `GameRound.detect_collision` builds
a `contacts` dict over settled state, then a second loop applies it, because "what meets what
cannot depend on the order they are asked in". Detonation wants the same treatment rather than
something invented for it.

**Which branch consults it.** `MachineInSpace.take_impulse_from` routes a collision into
`take_damage_from`, so a missile that flies into a planet dies with `is_destroyed` true and the
chain branch above detonates it (ADR 0023 says so outright). A disabled missile must not go off
there either, so the warhead reads its own `status_effects` rather than anything checking at the
point of damage.

**Still open: which component a disabling hit lands on.** For a missile or a mine it does not
matter, because disabling all of them is disabling the warhead. A ship is the problem: disabling
every component at once is not "lose a turret". The object decides what an incoming effect means
for it, the way ADR 0023 has it decide what an impulse means, so `Ship` answers this differently
from `Missile` when ships become targets. Not needed while only ordnance can be disabled.

**A laser disables, and that needs no new concept.** `DamageType.Laser` joins Explosion,
Nanocyte, EMP and Impact, saying what hit you like the other four do. Ordnance answers it by
setting `DISABLED` on its own components as well as dying, so the warhead does not fire. A ship
answers the same hit as plain damage. Nothing has to model "disabling" as a kind of harm, because
it is what a missile decides a laser means, which is `take_damage_from`'s existing shape and ADR
0023's rule one level up.

That makes every laser a missile-killer, not only a point defence mount. The families stay
distinct on arc, heat and damage instead, which is a better split anyway: a duellist that happens
to swat a Splinter on the way in is fine, a duellist that is also the best anti-missile gun is not.

**A bug on the way in.** `laser.py:70` passes the string `'Laser'` where every other `HitEvent`
passes a `DamageType`:

```python
HitEvent((self.container.pos, target_ship.pos), 'Laser', self.owner, target_ship, ...)
```

So a laser hit is the only one whose `_type` is not a member of the enum, and every
`hit_event._type == DamageType.X` comparison quietly does not match it. That costs nothing today
and would break this the moment a laser hit is meant to be recognised.

## Not in this plan

The nanocyte phase change and the deal order in `five_faction_war.py` are real and documented in
the assessment. They are registry and constant tuning, which is worth doing once the registry
rewrite settles.

A tender: a ship that replenishes other ships in the field. `Replenisher` is a Protocol and only
`Starbase` implements it, so it is a small change. Deliberately not now. Replenishing at a base is
a pitstop, and the choice of when to take it is the point; a tender that follows the fleet around
would dissolve that. Worth a scenario of its own later.