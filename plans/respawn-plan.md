# Respawning

Working document. Edit it directly; this is what we iterate on.

## Decided

**Both roster files become JSON Lines**, one object per line. Positional whitespace cannot express
an absent field, which is the bug we hit in `players.txt`; spawns need optional fields from the
start (no player, no faction, later a scenario trigger) and ships will follow. The console builds a
roster structurally now, so nobody hand-crafts a ships file any more.

Two files, same format, different lifecycles, and the difference matters:

- `ships.jsonl` is the round-0 roster. **Rewritten** whole, because setup writes the scattered
  coordinates back into it so placement replays.
- `spawns.jsonl` is a log of arrivals. **Appended**, never rewritten, so two directors clicking
  spawn at once cannot corrupt each other and a truncated write costs one line.

**The paste box is gone**, and with it the argument that a formal format makes hand-pasted input
checkable. Nobody hand-writes a roster, so JSONL now rests on one leg only: positional columns
cannot say "this ship has no player", which step 4 needs and step 6 needs again.

The format never crosses the seam either way. The console formatting rows back into a file blob
was the thing to fix, not the paste box, which only ever filled the table in the browser.

**The missile offset goes in now.** No games are in flight, so nothing regenerates into results a
player has already read.

---

## Context

The game is brutal and a destroyed ship ends a player's involvement. We want ships to come back, in
two ways:

- **An admin action**: the director spawns any ship type and assigns it to any named player.
- **A starbase component**: a player fires it and gets one ship back, of the type that was killed and
  belonging to whoever owned it. Once per wreck, and at most three per game.

The narrow rule is deliberate. It prevents arbitrary type choice, arbitrary owner choice, and
spawning a fleet by writing ten Fire orders. The three-spawn limit is what stops a game running
forever. The same component shape serves a carrier's hangar later, with a different source of what it
may spawn.

Score dilution is the price of dying: the wreck keeps its score in the graveyard, the replacement
starts at zero, and a leaderboard that divides by ships commanded punishes the death.

### Owner is not player

Two different things that must not be conflated:

- `owner` is a reference to an object in space. A missile's owner is the firing ship; a mine's owner
  is the layer; a **ship's owner is itself** (`Ship.__init__` passes `owner=self`). Warheads and
  scoring read `ois.owner.faction` through it.
- `player` is a person's name, and only a ship has one.

A spawned ship is therefore an ordinary ship: it owns itself, and it carries the wreck's `player` and
`faction`. Nothing about the spawn changes what `owner` means.

---

## Step 1: a launched thing appears clear of its own reach

`Launcher._create_missile` (`launcher.py:27`) puts the new object on the launching ship's exact
position. A `RocketWarhead` has a range of 20 with flat falloff, so a rocket that triggers on
its launch tick takes 50 off its own launcher. Any enemy within the fresh rocket's range detonates it
on top of the ship that just fired it.

The rule: **placed at its own reach plus one, along the launch heading.** Minimum distance with
no self-kill, and zero for anything that reaches nowhere. A Rocket goes out 21, a Splinter 7.

**Reach is a question every component answers**, per
[ADR 0019](../docs/adr/0019-machines-drive-components-through-one-vocabulary.md). The first draft of
this step put `blast_range` on the `PayloadType` protocol and implemented it on `MissileType` and
`MineType`. Wrong three times over: it widens a `runtime_checkable` protocol, it asks a type object
whose `weapons` property builds throwaway components on every read, and it names the question after
warheads so that a component which heals or tows or spawns at 20 units cannot answer it.

`Component` gets a neutral default, in the shape `Weapon.ammo` already uses:

```python
# How far this component reaches into space on its own initiative. A machine is born clear
# of its own reach, see Launcher._create_missile.
range = 0
```

`Warhead.range` already shadows it with the number it has always had (`warhead.py:82,89,96,103,110`),
so no warhead changes. A machine reports the widest reach it carries:

```python
@property
def range(self) -> int:
    return max((c.range for c in self.all_components.values()), default=0)
```

`all_components`, not `weapons`, because the next thing with a reach may well not be a weapon.

The launcher creates the payload at the ship's position and then moves it out by
`payload.range + 1`. Nothing asks a type object anything, and `PayloadType`, `Weapon` and
`MachineType` stay untouched.

Not `max_speed // 2`, which was the first idea: a `NanoMissile` flies at 60 but its warhead reaches
50, so half a tick's travel would still take 70 hull off its own launcher.

**Delete `explode_distance` and `explode_damage`** from every missile type while we are here
(`registry/missiles.py`). Nothing reads them; they are leftovers from before warheads were factored
out, and they now contradict the warheads that replaced them — `NanoMissile` says 6 against its
warhead's 50, `EMPMissile` says 20 against 10.

`MineType.max_scan_distance` (`registry/mines.py:18`) reads `self.weapons[0].range`, which is the
same mistake this step is avoiding: it asks the type, builds a throwaway warhead to read a number
off, and takes index 0, so a `NanocyteMine` reports its Splinter's 6 rather than its Nanocyte's 50.
Once a machine answers `range` this becomes `self.range` on the instance. Fixing it moves scan
ranges and therefore outcomes, so it goes on the TODO rather than riding along here.

**The launcher places, the type sets speed.** Position moves out of the type objects entirely.
`MissileType.create` keeps `replace(vector, speed=self.max_speed)` and `MineType.create` keeps
`vector.accelerate(-self.slow_down_rate)`, because launch speed genuinely differs by payload and the
same `Launcher` lays mines and fires missiles (`Launcher('M1', SplinterMine(), 10)` in five
registries). Neither touches position any more.

Warrants a comment on the offset, since it looks arbitrary and someone would undo it: a thing born
inside its own blast radius kills its launcher.

**Done, and it pulled three more changes with it.** The two replay tests failed as expected, and
reading the differences was worth it, because the numbers were never the point:

- The offset shifted where rockets sample their range, so they started detonating past the target
  and hitting the opposite shield. That was the **tunnelling bug** on the TODO, now fixed:
  `ObjectInSpace.approach_fraction` and `position_at` answer where two paths first closed to a
  given distance, `moved_from` holds the start of this tick's travel, and warheads go off at first
  contact rather than wherever the tick happened to end. `../test/engine/ois/test_warhead_path.py`.
- Both replay games then stopped killing their target, so their scenarios gained a third volley.
  That exposed a **negative score**: `min(amount, self.hull)` on a corpse whose hull had gone
  past zero. Now `Ship._damage_hull`, which scores for hull that was there to remove.
- Both tests asserted a hand-derived total that only holds for one exact damage sequence, since
  the shield pays half a point per hit rounded down. They now assert what the scenario is for:
  the target dies, its shield broke, and the score exceeds what those bonuses are worth.

Also settled: a blast damages everything in range, including your own ordnance, while the trigger
stays faction-filtered. [ADR 0020](../docs/adr/0020-explosions-do-not-take-sides.md).

---

## Step 2: the Tick reaches command execution

### What is wrong

`MachineType.create` takes a `tick` and defaults to `TICK_ZERO`, which is `Tick(0, 10)`. Nothing has
ever passed one, so every missile and mine ever launched starts its `History` in round 0.

A missile fired at tick T has `history.current` pointing at the `TickHistory` for `TICK_ZERO`. The
round's final loop calls `history.update()`, which writes the snapshot into `TICK_ZERO` rather than
into T. At T+1, `set_tick` updates `TICK_ZERO` once more and then moves on. **A missile has no entry
for the tick it was launched** and first appears on the map a tick later, already moved.

### What TICK_ZERO is actually for

It is the round-1 opening state. `get_ship_round` (`services.py:194`) renders a round's start from
`start_tick.prev_round_end`, which for round 1 is `Tick(0, 10)`, and that is precisely what
`GameSetup.run_tick_zero` writes. For a ship it is real and load-bearing.

For a missile it is spurious, and **a missile launched in round 1 currently renders as though it were
already sitting there when the round opened.** That is the visible symptom.

**Nothing about a missile's life depends on it.** `Missile.is_destroyed` is hull ≤ 0 or battery ≤ 0,
and `post_move` drains `energy_per_move` per tick. `Mine` is the same with `energy_per_tick`.
`Warhead.decide(ois, tick)` ignores its tick argument entirely. There is no lifetime, no expiry and no
age anywhere that reads a Tick.

### Why the change is contained

`GameRound.do_tick` (`round.py:36`) receives the real `Tick` and derives `tick_nr` (1..10). That
integer has two uses: indexing `ois.commands`, and being passed to `Command.execute`.

**The first stays.** That dict is keyed by the number the player typed in the command file, and
`Controller.add_command` (`control.py:26`) builds a command line from an int as well. Where an int is
genuinely the input it stays an int, taken from the Tick as `Gunner.fire_laser` already does with
`tick.tick + 1`.

**The second is dead.** Every `execute` body forwards `tick` to `super().execute(tick)`, and the base
implementation logs the command's text without mentioning the tick. No behaviour anywhere reads the
value. Changing its type cannot change an outcome.

The engine already carries the real `Tick` on the neighbouring hooks: `Ship.tick(tick: Tick)`,
`Component.decide(ois, tick: Tick)`.

### The change

- `GameRound.pre_move_commands` / `post_move_commands` take `tick: Tick`; `do_tick` keeps `tick_nr`
  for the `ois.commands` lookup and passes `tick` for execution.
- `Command.execute(self, tick: Tick)` across all seven commands; import `Tick` in `command.py`.
- `Weapon.fire(self, params, objects_in_space, tick: Tick)`, likewise on `Laser`, `Gravscan`,
  `Launcher`, and `Ship.fire` (which stays for now, see step 8).
- `Launcher._create_missile` passes `tick=tick` into `payload_type.create`.
- `MineType.create` has the wrong type hint, `tick: int = 0`, and `test/engine/ois/test_mine.py:11`
  passes a literal `1`. Both become a real `Tick`.
- Fix the stale `Weapon` docstring: it is a component that is actively triggered, not one that
  necessarily damages. Gravscan is the counter-example.

Reports change: missiles appear at their launch tick and position, and events their warhead records
on that tick are no longer written into round 0. Combat cannot move, because damage, scanning and
explosions read live positions and never history. If step 1's tests were made to pass and step 2
breaks them again, something did depend on it and we stop and look.

**Done, and nothing depended on it.** The replay tests stayed green and the scores are unchanged
hit for hit, which was the tripwire. `../test/engine/ois/test_launcher.py` proves a launched missile
and a laid mine now start their history at the launch tick, with the real launch position in the
snapshot, and no `TICK_ZERO` entry at all.

Two things came along:

- **`History.__init__` now asserts its tick is a `Tick`.** That is what caught the one remaining
  caller passing a bare int, `../test/engine/ois/test_mine.py`, and it stops the class of bug this
  step exists to fix from coming back quietly.
- **`Component.tick` and `Laser.tick` took a parameter called `tick_nr`** while `Ship.tick` had
  been handing them a real `Tick` all along. Renamed, same as the stale `Weapon` docstring.

The tick is threaded rather than read from an ambient clock on purpose: rounds are deterministic
(ADR 0002) and the engine already passes it to `Component.decide` and `Ship.tick` the same way.
The alternative considered was having the launcher read it back out of `self.container.history`,
which needs no signature changes but makes the reporting structure the clock.

---

## Step 3a: the roster crosses the seam as records — done

`ship_records` (`admin_ui/app.py`) returns validated dicts, `create_new_game` and
`AdminService.create_game` take `list[dict]`, and `ShipFile(gd, ships)` takes records. The console
no longer knows what a roster file looks like. `SHIP_FILE_HEADER`, the `'\n'.join`, the paste box
and its CSS, the dead `ships_to_lines`, and `ShipFileLine.__str__` and `.move` are all gone.

Nothing on disk moved: `load` still reads whitespace columns, through
`records_from_columns`, which is the one function 3b replaces.

Two things came out of it:

- **A non-numeric coordinate used to be a 500.** The console wrote it into the blob unchecked and
  the engine raised on `int()`. It is a message now, next to the unknown-type one.
- **`../test/engine/test_admin.py` asserted on whitespace column counts**, which 3b deletes. Rewritten
  to assert what survives both steps: given coordinates come back unchanged, and ships without
  coordinates get placed and the placement is written back. It ran against the committed
  `test-game-2` directory; it uses a temp directory now, and the flaky "no coordinate is exactly
  zero" assertion became "the ship is not still at the origin", which cannot flake.

Also updated: `../test/app/test_game_pulse.py` and `../test/engine/test_run_test_games_2.py` passed
blobs across the seam.

---

## Step 3b: ships.txt becomes ships.jsonl

One object per line, no header. The keys are the header. Entirely inside the engine now.

```jsonl
{"name": "Blaster", "type": "H2545", "faction": "One", "player": "Serge", "x": 1, "y": 0}
{"name": "Sentinel", "type": "SB2531", "faction": "Two", "x": 0, "y": 0}
```

`player` is optional and its absence means an NPC hull, which is exactly what step 4 needs. `x` and
`y` are optional; absent means the engine scatters the ship and writes the coordinates back.

**Done.** `load` is a `json.loads` per line, naming the file and line number when one will not
parse. `save` is a `json.dumps` per ship and leaves `player` out when there is none, which is the
shape step 4 reads. `records_from_columns` and `ship_file_with_coordinates` are gone,
`INIT_FILE_NAME` is `ships.jsonl`, and all nine rosters were converted and replayed.

Two things found on the way, both on the TODO:

- **The CLI form in `../CLAUDE.md` does not work.** `python -m arena.cli.main setup xke` fails with
  `invalid choice: 'xke'`: `action` is `nargs="*"` ahead of an optional `gamedir`, so argparse
  takes both words as actions.
- **`setup_game` before `regenerate_game` replays nothing.** Setup cleans the pickles, so
  `regenerate_game` reads its target round as 0. Process rounds forward instead, the way the CLI's
  `generate` does.

`../docs/adr/README.md` now says the never-edit rule protects the reasoning, not a path: a renamed
file gets renamed in ADRs too.

**Also touched:** `INIT_FILE_NAME` in `arena/cfg.py:54`; `ships_to_lines` in `admin.py:62`, which is
dead code and goes; `ShipFileLine.__str__`, which formats the CSV-ish line `ships_to_lines` used.

**Data conversion.** Six test games hold a `ships.txt`: `apitest`, `scenario`, `test-game`,
`test-game-2`, `test-game-3`, `xke`. A throwaway converter writes the `.jsonl` beside each and the
`.txt` files are removed; the pickles regenerate under the standing policy. Four tests write a ships
file inline and need the new shape: `test/app/test_archiving.py:19,44`, `test/admin_ui/test_gate.py:20`,
`test/api/test_login.py:28`.

Doing this before step 4 means an absent player is already expressible when
`is_player_controlled` starts reading it.

---

## Step 4: a ship knows its owner when it is built

`Ship.is_player_controlled` returns `True` unconditionally (`ship.py:50`) and `player` is grafted on
after construction by `GameSetup._init_ships` (`admin.py:102`). Hence the `getattr` reads at
`services.py:175` and `:177`.

**Done.** `player` is a `Ship.__init__` argument, `is_player_controlled` returns `bool(self.player)`,
`_init_ships` passes it through `builder.create`, and all seven `getattr` reads in `services.py`
are plain attribute access.

`faction` was **not** moved. This plan said to pass it through the constructor too; that was wrong.
Every reader outside a ship gets it through `owner` (`warhead.py:54`, `missile.py:100`,
`event.py:118`, `services.py:309`), and a ship's owner is itself. `ObjectInSpace.faction = None` is
a placeholder so those reads do not explode, not something an object in space has. It stays
assigned after construction.

The thing this uncovered: **`Game.load_commands` demanded a command file from every
`isinstance(s, Commandable)` ship**, while `missing_command_files` asks `player_ships`. So a round
reported itself ready and then failed on a missing file for the hull nobody commands. It now reads
a file only for a ship with a player, and hands the others an empty command set, because their own
Controller components may still add commands as the round runs. One of the `isinstance` violations
on the TODO, found by using it.

`../test/engine/test_npc_hull.py` covers the whole path: a player-less hull is not a player ship, no
orders are expected for it, the round processes with only the players' orders in, and the roster
written back still has no `player` key for it.

---

## Step 5: the graveyard is reachable — done, by a different route

The wreck's name is the lookup that establishes ownership. Its graveyard entry carries the type, the
player and the faction, so `ShipSpawner` needs no player registry and the engine never reaches above
itself.

**This plan proposed threading the graveyard alongside `ois` as a second thing**, with a
`graveyard`/`needs_graveyard`/`set_graveyard` trio on `Parameter` mirroring the `ois` one, and the
round holding a copy. All of that was wrong, and rejected in the doing:

- The graveyard spans rounds, so it never belonged on `GameRound`.
- Two channels for "what the world contains" is one too many. `ois` was already the channel for
  asking about the world; it was just a bare dict with no room for a second question.

**What was built instead: a `World`.** `objects` and `graveyard` on one object, passed down every
engine hook in place of the dict, with `add` / `remove` / `add_to_graveyard` / `move_to_graveyard`
for changing it and `known_to(ship)` for the wider view a player may name. 38 signatures.

Three things fell out:

- **`_known_names` is gone.** It faked a wider world by passing a different dict as `ois`. The
  distinction is now explicit: `is_valid` checks `known_to(ship)`, `value` reads `objects`, so an
  order aimed at something already destroyed is still accepted and still fizzles when fired.
- **The world is pickled whole, once per round**, so `graveyard.pickle` is gone. A round's wrecks
  are the ones that had died by then. Reviewing round 2 of `xke` used to show the three wrecks it
  has now; it shows none, which is what was true then.
- **`Game.update_graveyard` is gone.** The round moves a destroyed ship at the point it leaves
  space rather than reconciling a list at the end.

**The claim flag is not in yet.** One boolean on the wreck, `replaced`, is what the mechanic needs,
and nothing reads or writes it until `ShipSpawner` exists. It goes in with step 7, as instance
state on the ship (see [docs/information.md](../docs/information.md)).

---

## Step 6: spawn, the admin action, and spawns.jsonl — draft

Two things in the first draft of this step are wrong now that `World` exists. Both are called out
below where they bite.

### Why a file at all

A world pickle is derived: `regenerate_game` throws the pickles away and replays from `ships.jsonl`
plus the command files. So a director's spawn has to live in a source file or it vanishes the first
time anybody regenerates. That is the whole reason `spawns.jsonl` exists, and it is also why a
`ShipSpawner` firing (step 7) must **not** be written there: its Fire order is already in a command
file, and recording it twice would spawn it twice on replay.

### spawns.jsonl

At the game root, read and written whole, the same way `ships.jsonl` and the world are. An earlier
draft had it appended for safety against two directors spawning at once; consistency of the storage
API is worth more than guarding a race that one director cannot have.

```jsonl
{"round": 3, "tick": 1, "name": "Voyager-2", "type": "A2527", "faction": "One", "player": "Rik", "x": 479, "y": 121, "heading": 90}
```

`player` and `faction` are optional, `heading` and `speed` default to 0. `round` and `tick` are what
make the replay land in the same place.

### Who reads it

**Not `GameRound`.** That was the first draft, and it is the same mistake step 5 made: a round
reaching for game-level storage. Spawns follow the path commands already take. `Game` owns the
directory, reads the file, builds the ships, and hands them to the round:

```python
GameRound.do_round(ship_commands, spawns)      # spawns: {tick_nr: [ship, ...]}
```

`do_tick` then does `world.add(ship)` for that tick before the pre-move phase. The round never
learns what a file is, and never constructs a ship.

`Game` reads the whole file and keeps the round it is processing. The file holds one line per
arrival for the life of the game, so there is nothing to page through.

`GameSetup` does not read it: round 0 comes from `ships.jsonl` alone.

### The capability

One function beside `builder.create`, taking a type name, a name, a `Vector`, a player and a
faction, returning the ship. Used by `Game` for the file, by `ShipSpawner` in step 7, and by
scenarios later. The `Vector` carries heading and speed, so a spawn always says which way it faces.

### Naming

**The director names an admin spawn.** It is arbitrary: any type, any player, so there is no wreck
to take a stem from and nothing to derive.

What the engine owes is the check. A name must not be one the game has ever used, because command
files are `<ship>-commands-<n>.txt` and a reused name would inherit a dead ship's orders.

**The world knows every name**, now that it holds objects and graveyard together: anything that
ever existed is in one or the other. So the check is `world.objects` plus `world.graveyard` and
nothing else needs consulting. Belongs on `World`, next to `known_to`.

Step 7 derives its name instead, since it has a wreck: strip a trailing `-N` for the stem, then
take the lowest N from 2 upward that this check says is free. `Voyager` becomes `Voyager-2`, and
`Voyager-3` if that one dies too.

### Who is in this game

`_roster` (`services.py:56`) reads `ships.jsonl` and feeds five callers: which games a player is in,
whether a name is claimable, who owns a ship, who is owed a login link, and the console's poll.

**The first draft said to union `ships.jsonl` with `spawns.jsonl`. That does not hold.** A ship
created by `ShipSpawner` is in neither file, by design. Union the two files and the console's poll
still cannot see a respawned ship, which is the whole point of the feature.

The source of truth is the world. It holds every ship that exists and, since step 5, every ship that
ever existed, so it answers for roster ships, admin spawns and spawner spawns alike:

```python
def _roster(self, game: str) -> dict[str, str]:
    world = self._gd(game).load_current_world()
    if world is None:
        return {}
    return {s.name: s.player
            for s in (*world.objects.values(), *world.graveyard.values())
            if s.is_player_controlled}
```

This reads a pickle where the ships file was a text parse, and the three cross-game callers do it
once per game. None of them is on a path that runs during a round: they answer "which games is this
person in", "is this name free", and "who is owed a login link", all of which are the director
clicking something. Not a cost worth designing around.

What it changes: a game set up but never processed still has a round-0 world, so it answers the
same. A directory holding a roster and nothing else now answers empty rather than listing ships,
which is more honest than it was.

### The admin action

`AdminService.spawn_ship(game, name, ship_type, player, faction, x, y, heading)` appends one line,
validating the player against `PlayerRegistry` and the name against what the world has used. The
registry lookup lives in `../arena/app`, where that knowledge belongs.

A ship spawned into round N appears during round N and takes its first orders in round N+1. That
falls out on its own: it is not in the world when round N's readiness is checked, so nothing waits
for orders it cannot have.

### Spawns are not only ships

Asteroids, space stations, planets, whatever a scenario wants to put in the world. That rules two
things out.

**The capability cannot sit beside `builder.create`.** That resolves against `all_ship_types`,
which is 20 names out of 30 `MachineType` subclasses, and a planet will not be a machine at all.
Spawning needs a resolver that is not ship-shaped.

Nothing but ships is spawnable today, though, so building the general registry now is speculative
against types that do not exist. Keep the file and the flow type-agnostic, since `spawns.jsonl`
already carries `type` as a plain string, and put the lookup in one function that widens later
without any caller changing.

**Two things survive untouched.** `_roster` filters on `is_player_controlled`, so a spawned asteroid
is not a roster entry. `leaves_a_wreck` defaults to `False` on `MachineType`, so nothing but a ship
clutters the graveyard.

### An object in space already knows when it arrived

Nothing needs storing. `ObjectInSpace.__init__` takes the tick an object comes into being and opens
its history there, so `history.first` is when it turned up and `history[history.first]` is where.
`TICK_ZERO` for anything the game was set up with, a real tick for anything later, which has been
true of every missile since step 2.

When something wants to ask, it is a derived answer over history and not a field:

    spawn_tick  ->  self.history.first

A stored copy would be a second fact about the same thing, free to drift. The one argument for
storing it is that `history.first` belongs to the recorder, and pulling the timeline out of the
entity is on `../TODO.md`; that is a reason to re-home the property if it happens, not a reason to
duplicate now.

**Not in this step.** Score dilution and arrival markers do not exist yet, so nothing reads it.
It goes in when step 7 or the leaderboard asks, which is the same rule the rest of this plan
follows.

Nothing open.

## Step 7: ShipSpawner

`ShipSpawner(Weapon)` in `objects/components/`, listed in `SB2531.weapons` (`registry/bases.py`) as
`ShipSpawner('SS', 3)`. `SS` is free: the base carries Shields, L1, L2, S1, S2, R1, R2 and G.

- Order: `Fire SS <wreck> <direction>`.
- `DeadShipParameter(Parameter)` — subclassing `Parameter` directly, since its value is an object in
  space, not a component. Its `kind` is a new `'dead_ship'`, which is how the UI knows to offer a list
  of claimable wrecks rather than a text field. Valid when the name is in the graveyard and not yet
  `replaced`, with feedback saying which of the two failed.
- Placement: 10 units off the base along `container.heading + direction`, heading the same direction,
  speed 0.
- Type, player and faction come from the wreck. Nothing about the new ship is chosen by the player.
- Three spawns, counted down like a launcher's ammo, and reported in `status`.
- **No `reset()`**, so a replenish can never refill it. `Starbase.replenish` resets the weapons of the
  ship it replenishes, so this only matters if a base is ever replenished by another base, but the
  rule costs nothing.
- On success: create, set `wreck.replaced`, record an `InternalEvent` on the base naming the player
  and the ship, return the ship so `FireCommand` puts it in `ois`.
- On refusal: `InternalEvent` and `None`, as `Launcher.fire` does.

---

## Step 8: documentation and the TODO

`../docs/data.md` rewrites the roster section for JSONL and adds the spawn file. `../docs/architecture.md`,
`../docs/README.md` and three ADRs name `ships.txt` in passing and need the new name. `../TODO.md`:

- Tick the in-game spawning entry; note the carrier hangar and the scenario spawn source as what
  comes next.

Everything else this plan turned up is already in `../TODO.md`, under Engine and under Making a game
easily: wrecks on the battlefield, `Ship.fire` with the `Commandable` protocol, parameter naming,
`MineType.max_scan_distance`, roster tooling, the five places that name a component, and the
mutable `Vector` / `Point`. This file is scratch and is not committed, so nothing durable stays
here. `owner` versus `player` moved to `../docs/glossary.md`.
One of those five matters to this plan specifically: `Missile.decide` reaches for `'warhead'` by
name, so a missile carrying a spawner or a healer alongside a warhead would only ever run the
warhead.

---

## Verification

After every step:

```bash
uv run --group test python -m unittest discover -s test -t .
```

Step 1 moved outcomes in the two replay tests and they were rewritten to assert the bonuses rather
than a total; every later step is expected to move nothing.

Step 3: after converting, `setup` then `generate` each test game and confirm the coordinates are
written back and the replay is identical. Create a game through the console and check the file it
writes.

Steps 5 to 7, end to end on a test game:

```bash
uv run python -m arena.cli.main setup <game>
uv run python -m arena.cli.main generate <game>
```

- Kill a ship, write `1: Fire SS <wreck> 90` in the starbase's command file for the next round, and
  generate. The replacement is in the round pickle, sits 10 units off the base facing the given
  direction, and the round after refuses to process until it has a command file of its own.
- Order the same wreck twice: the second is refused with feedback, not silently ignored.
- Spend all three spawns and try a fourth.
- Regenerate the game. The respawn happens again at the same tick with the same name, and does not
  happen twice.
- Spawn through `AdminService.spawn_ship`, check the line in `spawns.jsonl`, regenerate, confirm the
  ship reappears once and only once.
- New unit tests under `../test/engine` for the naming rule, the claim, the limit and the refusals;
  under `../test/app` for the roster union.