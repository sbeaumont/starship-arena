# Setting a game up from a scenario

**Built, and the durable parts have moved out.** The decisions live in
[ADR 0021](../docs/adr/0021-scenarios-sit-in-the-services-layer.md) and
[ADR 0022](../docs/adr/0022-a-game-directory-moves-between-three-places.md), the file formats in
[docs/data.md](../docs/data.md), and what is left in [TODO.md](../TODO.md). What is kept here is
the reasoning that was worked out along the way and would be tedious to reconstruct.

Three things this plan got wrong, which is the useful part:

- **Scenarios were put in the console** on the argument that the storyteller may know things no
  other interface does. They lasted until players registered through the API. Now ADR 0021.
- **The signup was keyed by scenario**, with the game named at the end. A game directory named up
  front and moved when it starts is one mechanism instead of two. Now ADR 0022.
- **Each scenario was to bring its own setup screen.** Once assignment became columns and a pool,
  one screen served every scenario, and the per-scenario template was deleted unused.

## Decided

**Races stay lore.** Nothing in `arena/engine` learns what a race is. The five registry modules
keep being a filing convention and nothing reads their names. A scenario is the storyteller, and
it is the scenario that says "the Human line is these four hulls, and it flies as one faction".

That also settles where the race-to-faction table lives: in the scenario, written out by hand.
A new ship type has to be added to it deliberately, which is right, because the thing you are
deciding when you add it is which side gets to fly it.

**Four steps, in order.**

1. **Open registrations.** The director picks a scenario and opens it. Nothing else is decided.
2. **People register.** A player picks an open scenario in the game UI, says how many ships they
   want and names each one, and puts themselves down.
3. **Assign.** The director sees a block per registration, player name and ship names, and drags
   each one into a faction column. Whoever is left in the pool is distributed at random on OK.
4. **Tweak and start.** The existing new-game screen with every row filled in, plus the game's
   processing settings, and a button that starts it.

Step 4 stays exactly what it is today: the roster is authored in one place, and the director gets
to edit anything before pressing the button.

**The Five Faction War is the first scenario.** Players spread over the five races. A faction with
nobody in it is not in the game. Every faction that is in the game has a starbase, commanded by
one of its own players.

**Signup comes from the players.** The director opens a scenario, people put themselves forward
with a request for up to 3 ships and a name for each one. Requests are trimmed so factions come
out level. Everything is random in this version; letting friends land in the same faction comes
later.

**Which factions are in is the director's call**, and it is answered by the assignment: a column
nobody ends up in is a faction that is not in the game.

**The starbase goes to whoever came out with the fewest ships**, and the director can move it,
which needs no new control: the roster rows on the last screen are editable, so changing the
starbase's player is typing a different name.

**A starbase is not part of anyone's tally**, and no faction has a ship cap. The only rule is that
factions come out level. This is meant to carry a lot of players.

---

## What exists to build on

`ship_records` (`admin_ui/app.py:105`) already turns submitted rows into `ships.jsonl` records, and
`AdminService.create_game(name, ships: list[dict])` already takes those records. So a scenario's
whole job is to produce a `list[dict]` and hand it to the screen that is already there.

`GameSetup.distribute_factions` (`engine/admin.py:49`) scatters factions evenly on a circle of
radius 500 and writes the coordinates back. Scenarios leave `x` and `y` out and get that for free.

An unowned hull is legal since the respawn work, but it is the wrong choice for a starbase: only a
commander can fire the `ShipSpawner`, and a faction whose base nobody commands loses its respawns.

---

## Step 1: scenarios, and the wizard around them - done

`arena/admin_ui/scenarios/` holds the package, `/scenarios` lists what there is, and
`/scenario/<key>` runs that scenario's own screen and hands its roster to `new-game.html`.
22 tests in `../test/admin_ui/test_scenarios.py`, which were the first tests any console route
has had.

Two things came out of the doing:

- **The levelling bites harder than it reads.** Rik asking for three and Menno for one, over two
  factions, gives them one each: Menno's faction can never field more than one, so that is the
  level Rik is held to. Correct, and worth knowing before a signup fills up.
- **Ship names are `<Faction>-<n>` for now**, because the director's screen collects no names and
  reaching into the registry for a hull's class name would be a sixth `admin_ui -> engine` import
  for a placeholder. Step 2 brings the real names from the people who chose them.

### A scenario

One module per scenario under `arena/admin_ui/scenarios/`, each holding an object with a key, a
name, a blurb for the picker, the template for its own setup screen, and one method that turns the
director's choices into ship records. A plain list in `__init__.py` while there is one of them;
reflection when there are three, the way `registry/builder.py` does it.

Form parsing belongs on the scenario too. Screen 2 is unique per scenario, so a generic route
cannot know its fields.

### The Five Faction War

The table it owns:

```python
FACTIONS = {
    'Human':     ['H2545', 'H2552', 'H2535', 'H2527'],
    'Feline':    ['F2551', 'F2547', 'F2534', 'F2533'],
    'Amphibian': ['A2527', 'A2539', 'A2545', 'A2553'],
    'Reptilian': ['R2545', 'R2525', 'R2531', 'R2551'],
    'Insectoid': ['I2544', 'I2552', 'I2526'],
}
```

Insectoid has three hulls where the rest have four. That is one of the things the power review has
to look at.

### The dealer

Written once, with ship counts in it from the start, so step 2 has nothing to rewrite. It takes
entries of `(player, ships wanted, one name per ship)` and the factions the director ticked:

1. Shuffle the players and deal them round-robin. Faction sizes differ by at most one.
2. Work out the target every faction is levelled to. Everyone who signed up commands at least one
   ship, so no faction can field fewer ships than it has players, and no faction can field more
   than its members asked for. That gives

   ```
   target = max(most players in any faction, fewest ships any faction asked for in total)
   ```

   Nobody gets more than they asked for, so a faction whose members between them asked for less
   than the target fields what it has and comes out short. The director sees that on the last
   screen and can fix it by hand.
3. Everyone gets their first ship. Second and third ships are granted in a random order until the
   faction hits the target, so nobody is outgunned by an accident of who asked for three.
4. Ship types cycle through the faction's list, so a faction is mixed rather than four of a kind.
5. Each faction gets an `SB2531`, commanded by whoever came out with the fewest ships. It counts
   against nobody's tally.
6. No coordinates. Setup scatters them.

Fewer players than factions raises. An empty faction is the director having ticked a race nobody
can fly, and guessing which one to drop is not the dealer's call.

The shuffle takes a `Random` the caller passes in, so the tests can seed it. Random draws are fine
here: this authors a plan, it does not process a round, so
[ADR 0002](../docs/adr/0002-deterministic-rounds.md) is not in play. The coordinates get written
back into `ships.jsonl` exactly as they do today, so the game still replays.

### The screens

- `GET /scenarios` lists them. One card today.
- `GET|POST /scenario/<key>` renders that scenario's setup screen and handles its form.
- Submitting it renders `new-game.html` with `rows` filled in. The route already accepts a `rows`
  list and the template already loops over it, so this is the same page reached a different way.

In step 1 the Five Faction War screen is two checklists: which races are in, and which of your active
players are playing. Everyone gets one ship, named after its hull class. The signup sheet replaces
the player checklist in step 2, brings the real ship names with it, and the rest of the screen
stays put.

---

## Step 2: registrations - done

`registering/<game>/` holds `scenario.json` and `registrations.jsonl`, and starting the game moves
the directory into the data root. `GET /api/game/open`, `PUT` and `DELETE /api/game/open/<game>`
serve the player, and `OpenGames.svelte` sits at the top of the selector screen.

Two things came out of it:

- **Scenarios had to move down to `arena/app`.** They were in `admin_ui`, and a player registering
  through `/api/game` needs the scenario's ship limit, which would have made the API import the
  console. The engine still knows nothing about factions, which was the actual constraint.
- **`Entry` and `Registration` were the same class in two layers**, so `Entry` is gone. `ships` went
  with it: the number of names is the number of ships, and two fields could disagree.


### Where a game lives before it starts

A third place a game directory can be, beside the data root and `archived`:

```
registering/<game name>/
    scenario.json                   {"scenario": "five-faction-war"}
    registrations/<player>.json     {"ships": 2, "names": ["Voyager", "Pathfinder"]}
```

The game is named when registrations open, so it is a game directory from the first moment and
being in `registering/` is what says it has not started. **Starting it moves the directory** into
the data root, exactly as `archive_game` and `unarchive_game` move one in and out of `archived`.
Same mechanism, third location.

The registrations move with it and stay there, which is right: they are a plan under
[docs/data.md](../docs/data.md), the record of who asked for what, and nothing can rebuild them.

**A file per registration**, because two players registering in the same second would otherwise
read-modify-write over each other, which is the race `ready/` already solved this way. Registering
again overwrites your own file and nobody else's. One JSON object per file, so `.json`; `.jsonl`
stays for the files that hold a record per line.

`all_game_names()` has to count these, or a name in registration is claimable a second time and
the move at the end collides.

### The player's side

Open registrations show up on the game UI's selector screen, next to the games you are already in,
as something to join. Registering wants a login, so the name is the one you are signed in as. Two
new routes on `/api/game`: what is open, and here is my entry.

Up to 3 ships, one name each. Names are checked against each other and against everyone else's in
the same game, because a duplicate breaks the roster two steps later and the person who typed it is
the one who can fix it.

---

## Step 3 and 4: assigning, and starting - done

`/scenarios` names a game and opens it. `/registering/<game>` is the pool and the five columns,
plain HTML5 drag and drop, and only the assigned are submitted. `/start/<game>` writes the roster
and the settings and moves the directory into play.

The levelling is what surprises: one player asking for two ships alongside one asking for one
gives them a ship each, because the second faction can never field two. Correct, and it reads as
a bug until you remember the rule.

---

## Step 3: assigning

Five columns and a pool. A registration is a block: the player's name and the ships they asked for.
Drag it into a column, or leave it in the pool and the deal places it at random.

Plain HTML5 drag and drop, vanilla, the way the rest of the console is. The console has no
framework and this does not justify introducing one. The form submits a faction per player, blank
for anybody still in the pool.

The dealer mostly does not change. What it loses is the round-robin deal, which becomes: honour the
assignments, then spread the pool to even the head count. Levelling ship counts, hulls, starbases
and names all stay.

**The faction tick-list from step 1 goes.** An empty column is a faction that is not in the game,
which answers the same question without a second control that can contradict the first.

---

## Step 4: tweaking and starting

The new-game screen with every row filled in, plus the processing settings that live on
`game-overview.html` today (`process_hours`, `process_on_all_ready`), and a button that starts it.

Starting is three things in one submit: move the directory out of `registering/`, write the roster
through `create_game`, save the settings through `save_settings`. The last two are calls that
already exist.

---

## Open

**The last screen at 200 rows.** A row is a div with six inputs, and a big Five Faction War is five
factions of twenty people flying up to three hulls each. The screen will render it, and scrolling
300 rows to find the one ship you want to rename is another matter. Already on
[TODO.md](../TODO.md) under Making a game easily. Worth watching once a real signup fills it, and
not worth designing around before that.

**Dragging 60 blocks is not obviously better than typing.** The drag suits 15 people. If a signup
gets big the pool wants a "spread the rest" button that fills the columns in front of you rather
than at submit time, so you can see what you got and move a few. Cheap to add later and it needs
the same split underneath.

---

## Step 3: the power review, yours

The concern is real and it is not something the code can answer: a faction must not be handed the
beginner hulls by accident. The registry's own numbers are the starting point, and I can put every
type side by side (hull, shields per quadrant, speed, turn, delta-v, battery, generators, scan
range, and what each launcher carries) so the comparison is on one page rather than in five files.

What comes out of it feeds the table in step 1, and possibly a per-faction ordering so the first
ship dealt to a faction is comparable to the first ship dealt to every other faction.

---

## Verification

```bash
uv run --group test python -m unittest discover -s test -t .
```

`test/admin_ui/` has one file in it and it only checks the director gate, so the wizard's routes
would be the first console routes with tests. Flask's `test_client` makes it cheap: post the
scenario form, follow the redirect, assert on the rows that came back.

The dealer is worth unit tests of its own, and they are the ones that will catch a real mistake:
factions differ by at most one ship, everybody gets at least one, no name is used twice, every
faction has exactly one starbase and it has a commander, and nobody gets more ships than they
asked for.

Then by hand: deal a game, create it, and run `setup` and `generate` on it to confirm the roster
the wizard wrote is one the engine will play.