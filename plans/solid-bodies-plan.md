# Solid bodies, and running into them

A ring of five planets, impassable to everything. The first terrain the game has had.

The decisions are in [ADR 0023](../docs/adr/0023-a-collision-transmits-an-impulse.md): a collision
transmits an impulse, the object receiving it decides what that means, the bounce is a reflection
with restitution 0.3. This file is the order the work goes in, and the things that will bite.

## What exists to build on

`ObjectInSpace.approach_fraction` answers where along this tick's leg the gap to something first
closed to a given distance. A body's radius is that distance, so contact detection is already
written. `position_at` turns the fraction back into a point, and `place_at` puts an object there
with `moved_from` reset, which truncates its path exactly the way a thing that stopped should have
its path truncated.

`MIN_GAP = 0.1` already solves "a gap of nothing has no direction" for a warhead's bearing. The
same constant keeps a bounced object outside the surface rather than on it.

`Starbase` is the precedent for immovability: `turn`, `accelerate` and `move` are overridden to do
nothing (`starbase.py:21-31`), with a docstring apiece. A solid body is that plus a radius.

`Ship.take_damage_from` is the shape the impulse copies. The warhead hands over an event and the
ship decides what its shields do with it.

`GameRound.do_tick` runs every object through the same phases in one loop each. Collision wants a
phase of its own, straight after the movement loop and before weapons fire.

---

## Step 1: Vector owns the conversion - done

`Vector` holds heading and speed. Everything about bouncing is easier in x and y, so the
conversion goes on `Vector` and nowhere else.

- `delta` property: the tick's travel as `(dx, dy)`, using sin on x and cos on y to match
  `Point.translate`.
- `with_delta(dx, dy)`: the same position, travelling as that describes.
- `component_along(direction)`: how much of the travel runs that way, signed.

Geometry only. A first cut had `speed_into(normal)` and `reflect(normal, restitution)` on `Vector`,
which put a surface and a coefficient of restitution on a type that should know about neither. The
bounce is physics and belongs with the impulse, which is what owns the restitution. `Vector` hands
it the projection and the way back from a delta, and that is all it needs.

12 tests in `../test/engine/ois/test_vector.py`. Pure additions, no caller changes.

Speed can be negative: `Ship.accelerate` clamps to `±max_speed`, so a ship reversing at -20 on
heading 0 faces north and moves south. `with_delta` keeps the sign it was given, so a ship that was
reversing reverses out of what it hit. It backed in, it backs out, and the heading turns by the
same axis flip either way.

## Step 2: mass, and what it means to be immovable - done

`ObjectInSpace.mass` answers 0. `MachineInSpace.mass` answers what its type says, the way
`class_name` and `type_name` already delegate. `MachineType.mass` is 0 and `ShipType.mass` is 1.

Every ship is mass 1 to start with. The parameter does nothing until a ship type wants to differ,
which is the honest default rather than inventing a table of tonnages nobody has balanced.

Effectively infinite mass is what makes something immovable, and it is the same fact for an
asteroid and for a starbase: bolted down, and the world moves around it. `ObjectInSpace.is_immovable`
answers that, false by default. Expressing it as a property rather than as a number is what keeps
`inf` out of the arithmetic, where it would produce `inf/inf` and a NaN heading.

An immovable object never initiates a contact. It has no leg, so it cannot run into anything, and
the collision phase leaves it out. `Starbase` therefore needs nothing overriding: it already says
it does not move, and that answer now does the work in a second place.

**The pairing that fell out of this.** `radius` says things stop at me, `mass` says I can be
shifted, and both default to nothing. Solidity and immovability stop being classes of object and
become numbers an object carries, which is why there is no `SolidBody` type anywhere below.

## Step 3: a registry per family - done

An asteroid needs somewhere in the registry to live, and `builder.spawn` said in a comment that
only ship types were spawnable and *"this is where that widens"*. Widening it meant deciding how a
caller asks for one kind of model and not another, and that question was already being answered
badly in four places:

```python
appfacade.py  {... if not issubclass(st.base_type, Starbase)}   and its mirror image
manual.py     the same test, both ways
services.py   category='Starbase' if issubclass(st.base_type, Starbase) else 'Ship'
```

Starbases were `ShipType` with `base_type = Starbase`, so nothing at type level told them apart and
every caller reached into the class hierarchy, against invariant 8. Two of those four were in
`admin_ui`, and the `Starbase` import they needed was one of the five `admin_ui -> engine`
violations architecture.md counts.

`StarbaseType(ShipType)` now exists, `SB2531` derives from it, and each family answers `category`
for itself. `builder._models(root, *filed_elsewhere)` builds one registry per family and leaves out
anything filed under another, so `all_ship_types` holds 19 hulls, `all_starbase_types` holds 1, and
neither has to be filtered by anybody. `all_types` is the union, for spawning and for validating a
type name.

All four `issubclass` calls are gone, and with them two engine imports above the seam.
`services.list_ship_types` now reads `category=st.category`, and starbases turn up in it, which
they never did before.

## Step 4: the body itself - done

`ObjectInSpace.radius` answers 0, alongside `mass`. Anything with a radius above 0 is something
you stop at, and a point-sized thing simply has none. There is no supertype for solid things and
no `is_solid` anywhere: an object carries a size, and carrying a size is what makes it impassable.
The day ships get one, ship-versus-ship collision is the same code with no new idea in it.

`arena/engine/objects/body.py` holds `Body(ObjectInSpace)` and `BodyType`, built the way ships are:
the model is a type object (ADR 0003) carrying `radius`, `mass` and `restitution`, and the thing in
space asks it. `arena/engine/objects/registry/bodies.py` declares `Asteroid`, which is the right
word at this scale. `builder.all_body_types` is its registry, from step 3's `_models`.

`Body` answers `is_destroyed` false, `is_immovable` true, and `move` does nothing, the way
`Starbase.move` does.

`owner` is set to `self`, the way `Ship` does, because plenty of code reads `ois.owner.faction` and
a bare `None` owner raises. `faction` stays `None`, which is what step 5 is about.

The snapshot carries the radius, so whatever draws the map gets it from the API rather than from a
constant in the browser.

11 tests in `../test/engine/ois/test_body.py`, including a full round with terrain in it, because
a body sits in `world.objects` and every phase has to survive one.

Two things the doing turned up:

- **`BodyType` needs a `max_scan_distance` of 0.** `Warhead.explode` reads
  `ois._type.max_scan_distance` for every object in the world to decide who saw the blast, so a
  type without one raises the moment a warhead goes off anywhere near terrain. Zero is the true
  answer, since terrain observes nothing, but the reason it has to be answered at all is the
  reaching-through-the-type smell that `docs/information.md` already lists.
- **`all_types` had to be split.** It was the union used both for looking a model up by name and
  for listing what a director can field. An asteroid is the first model with no hull to describe,
  and `_specs` reads `max_hull` and `max_battery`, so the two meanings came apart:
  `all_fielded_types` is ships and starbases, `all_types` is everything and is what `spawn` uses.

A rocket fired past an asteroid already stops dead on it, at the centre rather than the surface,
because `Warhead.triggers_on` reads a missing faction as an enemy one. That is step 5, and it is
now demonstrable.

## Step 5: faction has three answers - done

`Stance` is an enum of `Friend`, `Foe` and `Neutral`, and `stance_towards` answers it.
`ObjectInSpace` returns `Neutral`, since nothing in space is on a side until something puts it on
one, and `MachineInSpace` shadows that with the faction comparison. Asked of the owner, because a
machine fights for whoever owns it. A `str` enum, so it can go straight into a DTO in step 8.

`Warhead.triggers_on` and `GuidedMissile.scan` both read `== Stance.Foe` and nothing anywhere
compares faction strings. Excluding yourself falls out: a thing is its own `Friend`, so a warhead
still cannot go off on its own launcher.

**A factionless ship is now neutral**, and that is a real change beyond terrain. `builder.from_plan`
takes `record.get('faction')`, so a director who spawns a ship without naming a faction gets one
that no warhead triggers on and no guided missile tracks. Correct by the rule in ADR 0023, and
surprising if you meant to add an enemy. Giving it a faction is the fix.

That surfaced in the fixtures: `create_ship_fixture` built two ships with no faction at all and
leaned on a missing faction reading as hostile. They now sit on opposite sides, which is what the
tests always meant.

18 tests in `../test/engine/ois/test_body.py`, including a rocket flying clean over an asteroid
and a Splinter refusing to lock onto one.

## Step 6a: a warhead goes off when its container dies - done

One line in `Warhead.decide`, and it settles three arguments at once.

The question that forced it: how does a missile that runs into a rock explode? Making detonation
the missile's answer to the shove meant `take_impulse_from` needed the world, which
`take_damage_from` does not, and the asymmetry had no honest justification. Making the warhead
notice contact with a surface would have detonated mines against rocks, when a drifting mine
should settle. Inventing an `absorbs` constant put a second number next to hull that means the
same thing.

None of that is needed. A warhead goes off when whatever it is riding is destroyed, and everything
else follows: impact destroys a missile, so it explodes; a mine that can take the tap survives, so
it settles; nothing reaches outward from `take_impulse_from`.

Two things checked rather than assumed:

- **Chain reactions did not exist before this.** A missile inside another's blast died without
  going off. ADR 0020's context says the second rocket *"dies to the first"* and never claims it
  detonates. Now it does, and shooting down a missile near your own hull is a real risk, which is
  what ADR 0020 already said was true.
- **A spent missile still fizzles**, with no code for it. `post_move` drains the battery after
  `decide`, so a missile that runs out is reaped before it can ever be asked again. Measured: 15
  ticks, battery 0, destroyed, no explosion.

Chains are order-dependent inside one tick, since `decide` is a single pass and a missile killed
after its own turn never gets another. That is the processing-order defect already in TODO.md
rather than a new one.

## Step 6b: the collision phase

A new loop in `do_tick`, after movement and before post-move commands.

Each object takes the earliest contact fraction over everything with a radius (`min`, the way
`Warhead.contact_fraction` does) and receives an `Impulse` carrying the source, the contact point
and a delta.

**The delta is the whole impulse**, which is what the ADR means by a direction and a magnitude. The
body works it out, so restitution never leaves the body and no receiver ever sees a coefficient.
Everything else falls out of the delta: its own direction is the outward normal, and a receiver's
impact speed is its `component_along` that direction. Below an impact speed of 5 the body uses a
restitution of 0, so a drifting mine settles against it instead of bouncing.

Then each type answers:

| | |
|---|---|
| `Ship` | add the delta to its travel, place at the contact point, take `mass × impact speed` as damage through a `HitEvent` |
| `Missile` | detonate where it hit |
| `Mine` | place at the contact point, speed 0 |
| `Starbase` | nothing to write: it is immovable, so it is never in the loop |

Damage needs a `DamageType`. `Impact` is a new member: `Ship.take_damage_from` matches Nanocyte and
EMP explicitly and sends everything else to the hull, which is right for a collision.

**The wrinkle:** a missile detonating in this phase damages whatever is near, which can destroy
another missile before that one has resolved its own contact. That is the processing-order defect
in TODO.md wearing a new hat. It does not make the existing problem worse and it does not fix it.

## Step 7: putting five of them in space - done

`bodies.jsonl` alongside `ships.jsonl`, read by `BodyFile` and built into the world by `GameSetup`
like everything else. Optional, the way `spawns.jsonl` is: a game without one is played on empty
space.

**The ring sits at radius 250, half way to the origin.** `distribute_factions` scatters factions on
a circle of radius 500, so a ring on that circle would drop a rock in somebody's lap. At 250 every
faction faces the same choice: go around the outside, or cut through the middle and thread the gaps.

The scenario owns it, so `FiveFactionWar.bodies()` returns the five records and `GenericGame` returns
none. `start_game` asks the scenario before it moves the directory, because that is where the
scenario file still is.

Nothing writes coordinates back the way ships do. A ship on the origin gets scattered and the
result has to be recorded for a regenerate to be deterministic; a body is never moved from what it
was given, so the file it came from is already the record.

6 tests in `../test/engine/test_terrain_setup.py`, including a regenerate.

## Step 8: the map, and neutral contacts - done

Bodies are scanned like anything else, so a rock is a `Contact` and fog of war applies to terrain
the same way it applies to ships. Nothing separate on `PlayerPlan`.

`Contact.friendly` was a bool, so it could only say mine or theirs and a rock came out as theirs.
It is now `stance`, carrying the engine's own `Friend` / `Foe` / `Neutral`, which is why `Stance`
is a `str` enum: it goes into JSON as it stands. `Contact.radius` comes with it.

**The map keys off the radius, not off a category name.** Anything with one is terrain, drawn true
to scale in the world layer under everything else, muted so it reads as something to fly around
rather than something to fight. That keeps `game-ui/CLAUDE.md` rule 4 honest: the size comes from
the API, and the day a body stops being a circle nothing here has learned a list of shapes.

`_stance` sits in the services layer because the engine answers between two objects and this asks
against every faction a player is flying. One place, rather than at each reader.

Left alone: `ScanInfo.friendly`, the per-ship view, has the same bool and the same blind spot. The
game UI does not read it.

## Step 9: one question for everything in range

Terrain and warheads both end a leg early, and only terrain does it before anything moves. A
warhead lets its container fly the whole leg and then pulls it back in `decide` with `place_at`.
The position is right three phases too late: scanning has already run, so the sighting other ships
recorded is where the missile was heading.

Seen in `Asteroid_Test`: two rockets that both killed Drifter at (0, -320) are drawn at
(1.3, -346), past what they destroyed, with the blast behind them.

```
scan      records the rocket at y = -346, where its full leg ended
decide    the warhead goes off and places it back at y = -320
snapshot  says -320, and nobody saw it
```

[ADR 0024](../docs/adr/0024-a-tick-advances-by-encounters.md) makes it one question asked of every
object, and a tick that advances by resolving what is in range.

**A second defect came out of designing it, and it is live now.** `Warhead.explode` decides who is
caught by asking each object where it was at the blast's fraction, computed against that object's
travelled leg. Those are the same thing only while everything flies its whole leg. Since bounces
exist they are not: a ship stopped at 0.3 has a leg spanning three tenths of a tick, so reading
position 0.6 off it runs past the end of a path it never flew. Nothing in the suite catches it,
because a blast and a bounce have not yet happened to the same object in the same tick.

Three dead ends, kept because each looked right for a while:

- **A sub-phase after the move**, so an interrupted object acts once everything has moved. It works
  and it means the decision is made in one phase and acted on in another, so the fact has to be
  carried or re-derived. Asking twice whether a warhead goes off is the smell that killed it.
- **Advancing the whole population to the earliest encounter**, keeping a global clock. Correct, and
  it moves objects that had no reason to move, which then need state to say where they got to.
- **Letting each object advance to its own next encounter.** Fastest to write, and it lets an object
  get ahead of a blast that concerns it, which forces either a per-tick history of segments or a
  rewind. The rewind is where the infinite loops live.

What survives all three: **do not move what has no reason to move.** An object that has not moved is
already complete.

The work:

- `Encounter(fraction, impulse=None)`, the answer to "when does something come within a range that
  matters to me".
- `ObjectInSpace.encounter(world)`, the first surface reached. `MachineInSpace` widens it to the
  earliest its components name. `Component.encounter` is None; `Warhead` shadows it.
- `ObjectInSpace` remembers the fraction of the tick it has used, and `position_at(fraction)` reads
  a moment in the tick rather than a point on a leg.
- `move` becomes "advance my leg by this much of the tick", and the impulse leaves it.
- `Warhead.decide` loses `place_at` and keeps only the chain trigger: a container that was
  destroyed. Going off on contact is an encounter.
- `GameRound.detect_collision` becomes the loop, and stops knowing what a radius is.

Four tests that should exist and do not:

- a missile's last sighting agreeing with where its blast is
- a ship bouncing and being caught in a blast in the same tick
- a surface and a trigger at the same fraction, both resolving in one pass
- a wedge: bounced off one surface into another at the same fraction, so the object spends the rest
  of the tick there

The last two are unreachable in play today. Five rocks of radius 40 sitting 294 apart cannot wedge
anything, which is exactly why the rule must not depend on the layout.

---

## Open questions

- **Does a wreck bounce?** A graveyard entry is not in `world.objects`, so it never collides. Fine
  for now, and slightly odd if a wreck is drifting.
- **What does a body do to a `ShipSpawner` respawn placed inside it?** Nothing checks. A ship
  spawned overlapping a planet would be found in contact on its first move with a leg, and bounced
  out, which is probably the right answer by accident.