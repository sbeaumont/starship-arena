# TODO

Running list of what is next. Newest thinking at the top of each section.

What is done is in [Done.txt](Done.txt), verbatim, and nothing here restates it. What is merely
wanted is under [Ideas](#ideas), which is not a queue: nothing there is promised, ordered or
started.

**No line numbers in this file.** `work` is outside the reference test's reach, so a citation here
rots with nothing to catch it. Name a symbol.

## Next, in order

1. **Finished games.** A game can be declared over, exported to a format that outlives the object
   model, and then walked through by anyone. Planned in
   [plans/finished-games-plan.md](plans/finished-games-plan.md). Detecting the end rather than
   declaring it is its last step, and it is where scenario triggers start.
2. **The Gunner and the Engage order**, which is what makes a laser worth aiming. It is also what
   makes a solo game's pirates shoot back. Detail under [Engine](#engine).
3. **Scenario builder**, now that a scenario is a real thing with a home.

## Game UI (`../game-ui`)

- [ ] **Nothing teaches.** The manual is a PDF behind a menu; the map explains itself to nobody. A
      first round with something pointing at the controls is the actual tutorial. The oldest thing
      a new player walks into.
- [ ] **You lose sight of your own ordnance.** Contacts are built purely from scans, so a rocket
      you fired drops off the map once it outruns your scan range: an H2545 sees 180 and its own
      rocket is past that by tick 4. Your own ships are already treated as ground truth rather
      than fog of war (`allies are ground truth` in `get_player_plan`); the argument for ordnance
      is the same. Decide whether it is everything you own or only what is still flying.
- [ ] **`internal` does two jobs.** It names a display category and it means "chatter you can
      switch off", which is why the log filters on `kind !== 'internal'`. Whether the kinds become
      log levels, and what a positive one would be called, is worked out in
      [plans/event-levels-plan.md](plans/event-levels-plan.md). A refused order being debug-level
      is the part that costs something today: every rejected `Fire R2` on Pi-tje was in the log
      and unread.
- [ ] **Shield quadrants are not drawn.** Boost is orderable now, but a player picks N/E/S/W off
      a list. Shields are **ship-relative** (N is the front ±45), so the map could draw the four
      faces rotated to the heading at that tick and let the quadrant be clicked.
- [ ] **Speed/throttle drag feel.** Dragging a node sets turn *and* speed at once; the speed
      half still feels rough. Oldest outstanding UI note.
- [ ] **Mine vectors are approximate.** A mine launches at the ship's speed *less*
      `MineType.slow_down_rate` (5), but that is not exposed, so the arrow reads ~5 units long.
      Exposing it cleanly needs a home that is not a superclass (see the rejected attempt in
      `MissileType`).
- [ ] **A launch arrow is drawn a whole tick of travel too long.** `FireCommand` runs in the
      post-move phase, so a launched thing is created after everything has moved and does not
      travel until the next tick. At the end of the tick you fire on, a Rocket is 21 units out
      (its blast radius plus one), not the 60 the arrow draws from `payload_speed`. A Splinter is
      7, and a mine sits at its offset too.

      The arrow wants the launch offset, and that number only exists on a *created* payload:
      `Launcher._create_missile` reads `payload.range + 1`, while `_weapon_info` has just the type
      object. Asking the type means building a throwaway payload to read a number off it, which is
      the "model constant that reads model parts" shape in
      [../docs/information.md](../docs/information.md) and the same defect as
      `MineType.max_scan_distance`. So decide where the number lives before adding the DTO field.
- [ ] **A gravscan cone is drawn at a made-up size.** `coneRadius` sizes the wedge off a constant,
      so it says nothing about how far the pulse really reaches: 1200 at 30 degrees down to 346 at
      360. The browser also invents its own granularity in `coneWidthAt`, a step of 5 the engine
      never agreed to.

      The reach cannot be sent as a formula, and it does not need to be: the setting is a
      `NumberInRangeParameter` over a finite range, so the engine can send the reach for every
      value it offers and the browser looks it up.

      `Gravscan.reach_of` now answers exactly that question, so what blocked this is gone: what is
      left is where the answer sits on the way out. "How far does an order to you reach at each
      setting it can take" is a question every component could answer, with a neutral empty for
      the ones whose reach does not move, and a `Gravscan` is a `Weapon` that is not really a
      weapon, so bolting it to `WeaponInfo` is the thing to avoid.
- [ ] **Per-ship standing orders** for `Pilot`/`Gunner` once those are live. `Pilot.target_name`
      and `Gunner.target_mode` already exist and are exactly this: per-ship settings, not per-tick
      commands, so they belong in a ship panel rather than on a tick.

## Engine

- [ ] **A Gunner, and the Engage standing order.** Lasers are unaimable, not weak. Orders are
      plotted ten ticks ahead against a captain choosing their own course, so nobody can know they
      will be 15 units away on tick 7. A missile forgives a bad prediction because it steers; a
      laser does not. Steep falloff was tried before and the fix was to raise the numbers, which
      is how one number came to mean both damage and reach.

      The answer is a crewman. A `Gunner` acts in `decide`, after everything has scanned, so it
      fires on where things actually are, and the player's job becomes positioning rather than
      tick-prediction. This is the laser's compensation for being short-ranged: every other weapon
      commits to a bearing ten ticks early.

      `Engage <gunner> <weapon> <target> <within> <shots>`. The gunner mans every laser on the
      hull, so it is not a scarce fire-control station and there is one per ship. `within` is the
      range inside which to open fire. `shots` is a budget **for the rest of the round**: ordered
      on tick 3, the laser fires at most that many times over ticks 3 to 10, and only on a tick
      where the target is inside `within`.

      Deliberately not in the game UI to begin with.

      `Gunner` and `Pilot` exist and no ship type carries either: `control` is empty everywhere.
      Two things to fix on the way. It queues for the tick after the one it decided in, which
      reintroduces the lag this is meant to remove. And it has both ADR 0019 violations that ADR
      names: `isinstance` to find its lasers, and `isinstance` to sort targets, where
      `category_name` already answers the second.

      **A solo game's pirates are the first customer.** They drift, get scanned and get shot, and
      nothing shoots back.

- [ ] **A laser sets a missile off instead of stopping it.** A laser is meant to disable ordnance:
      that is what makes point defence worth carrying. It does the opposite. `Warhead.decide` fires
      on nothing but "my container died and I am not spent", so a lasered rocket detonates where it
      stands, and `Missile.take_damage_from` has the `DamageType.Laser` in its hand when it zeroes
      the hull and throws it away.

      Ordnance that dies to a laser should mark its own warhead spent, which is the smallest form of
      the disabling hit and needs no new concept: the damage type already exists, already arrives,
      and the object deciding what a blow means to it is `take_damage_from`'s whole shape.

      Two things it does not fix, both worth knowing before writing it. **Inside the blast radius
      the missile still wins**, because `resolve_encounters` settles a proximity trigger a phase
      before any weapon fires - so point defence intercepts a tick early or not at all, which is
      the floor the ship balance plan works out. And **the shot is spent either way**: at point
      blank the laser fires into something already dead, pays full heat and energy, and says nothing
      about it.

- [ ] **Processing order must not affect the outcome, and today it can.** Not where it used to:
      `resolve_encounters` runs before anything moves and before any weapon fires, so a warhead's
      trigger is settled as a phase rather than as an accident of iteration, and something just
      launched cannot be caught by a blast this tick at all.

      What is left is the other detonation. `Warhead.decide` sets off a warhead whose container
      died, and the decide phase is a single forward pass: if one blast kills something whose
      `decide` has already run, that warhead never fires and, leaving no wreck, nothing records
      that it did not. Which way it falls depends on the order the world lists its objects in.

      `resolve_encounters` is the shape to copy - resolve, then look again, until nothing answers -
      and a chain of detonations needs exactly that loop or it stops at one link.

      Fixing the laser above narrows this to blast carrying to blast, which is the case the loop is
      actually for. Both live in `Warhead.decide`, so they are one sitting.

- [ ] **Ship against ship.** Collisions notice terrain but not each other. Wants the
      processing-order defect above fixed first. Gravity is a different feature; parked.

- [ ] **Five event filters ask what class an event is**, `ADR0019-c` to `ADR0019-g` in
      `../arena/engine/history.py`. `Event.kind` is abstract on the base and already answers it
      ([ADR 0010](../docs/adr/0010-objects-describe-themselves.md)), so the cheap fix is reading
      `kind`. The question worth settling first is whether that is the right question at all: what
      `History.add_event` wants to know is what an event counts towards, not what it is, and a
      component that scores some new way would want the same answer. Decide the question, then
      change the five together. Anchored, so the check is quiet until somebody adds a sixth.

- [ ] **A blast and a beam do the same three things twice.** `Warhead.explode` and `Laser.fire`
      each build a loud event, hand it to whoever it happened to, then loop every object in the
      world handing it to anyone whose passive reach catches it; `ExplosionEvent` and `BeamEvent`
      each answer `modify_scan_range` off their own `visibility`. Two callers is where a shared
      name starts being worth it and not before, so this is a note rather than a refactor: decide
      once whether being noticed is a question the world answers, an event answers, or neither.
      The loop also reaches through `ois._type.max_scan_distance`, which is the "reaching through
      an object's type" shape in [../docs/information.md](../docs/information.md), so whatever
      takes it over should ask the object instead.

- [ ] **A malformed Boost command crashes.** `Component` has a neutral default for `activation`
      and for `power_up` and none for `boost`, and `ComponentCommand._init_params` validates how
      many parameters a component wants rather than whether it takes this order at all. A
      `Gravscan` wants two as well, so `Boost <gravscan> <direction> <cone>` passes validation and
      then dies on the attribute. Long-standing.

- [ ] **A duplicate order for one weapon in one tick disappears silently.** Two `Fire R1 90`
      lines on the same tick produce one shot with no feedback, because `CommandSet.add` keys
      `weapons` by component and the second assignment wins. It is what made
      `test_run_test_games_2` wrong for a long time. Everywhere else a refused command records an
      `InternalEvent`; this should too.

- [ ] **`MineType.max_scan_distance` asks the type, not the mine.** It reads `self.weapons[0].range`,
      which builds a throwaway warhead to get a number off it and then takes whichever happens to
      be first, so a `NanocyteMine` reports its Splinter's 6 rather than its Nanocyte's 50.
      `MachineInSpace.range` already answers this on the instance. Fixing it moves scan ranges and
      therefore outcomes.

- [ ] **`Vector` and `Point` are mutable, so the heading guarantee has a hole.**
      `Vector.__post_init__` folds a heading into [0, 360), which covers construction and
      everything built through `replace`: `turn`, `move`, `translate`, `accelerate`. Assigning a
      field in place skips it, which is why `Ship.turn` still needs its own `% 360`. Freezing both
      dataclasses would close it and put every change through one door. The in-place assignments
      are in `Mine.slow_down`, `Ship.accelerate`, `Ship.turn` and `Missile._intercept`. Note
      `Ship.turn` normalises the *rounded* heading where `Vector.turn` uses the raw float, so
      consolidating the two shifts ship headings by fractions of a degree and moves every replay
      outcome.

- [ ] **Four places name a component instead of asking all of them.** Each is a spot where a new
      component is silently ignored, so they block the healer, the teleporter and the
      spawner-in-a-missile as much as they are wrong today. The list is in
      [ADR 0019](../docs/adr/0019-machines-drive-components-through-one-vocabulary.md) under *Where
      the code does not do this yet*. Two of them are in `Gunner` and go with that work.

- [ ] **Solid bodies block line of sight.** Deliberately left out of ADR 0023 so the first cut
      stays movement only. A planet you can shoot straight through is wrong, and hiding behind one
      is worth having. Touches scanning, lasers and the blast loop in `Warhead.explode`, and the
      game UI has to draw the shadow or players cannot plan around it.

- [ ] **A respawn placed inside a body is nobody's decision.** Nothing checks where
      `ShipSpawner` puts a ship. One overlapping an asteroid is found in contact on its first move
      with a leg and bounced out, which is probably right by accident rather than by rule.

- [ ] **Does a wreck bounce?** A graveyard entry is not in `world.objects`, so it never collides.
      Fine for now, and slightly odd once a wreck is drifting somewhere a player can see it.

- [ ] **`leaves_a_wreck` may need to be settable per ship.** It is a model constant on `ShipType`
      today, so every ship and starbase leaves a graveyard entry and no model can differ. A swarm
      of throwaway NPC hulls would want to opt out without becoming a new ship type. That means
      moving it to instance state in `Ship.__init__` and overriding the derived answer, which is
      an internal change: readers already ask the machine, and it crosses no seam. See
      [../docs/information.md](../docs/information.md).

- [ ] **`number_of_inputs` is dead machinery.** `BoostQuadrantParameter` was the only parameter
      consuming more than one word, and splitting it into a quadrant and an amount removed the
      last user. Four lines in `ComponentCommand._init_params` and a property on `Parameter` now
      serve a case that cannot arise. Delete, or keep deliberately as an extension point.

- [ ] **Parameter naming says the opposite of what it means.** `ComponentParameter` means "a
      parameter belonging to a component", while `ComponentSelectorParameter`, whose value *is* a
      component, subclasses `Parameter` directly.

- [ ] **NPC controllers build commands from text.** `Pilot`/`Gunner` format a string and hand it
      to the parser. If they go live, construct `Command` objects directly and add
      `Command.as_text()` for reports and logs. Validation lives in `Command.__init__` /
      `Parameter.is_valid`, not in the parsing, so nothing is lost.

- [ ] **`setup_game` before `regenerate_game` replays nothing.** Setup cleans the pickles, so
      `regenerate_game` then reads its target round as 0 and stops. Only bites a script that calls
      both; worth a line in `regenerate_game`'s docstring, or having it take the target round.

- [ ] **Separate history from the entities.** `ObjectInSpace` is both the live object and its own
      per-tick archivist. Staged plan: (1) pull the recorder/timeline out of the entity,
      (2) if replay and scenarios become central, make the timeline *derivable* by re-running the
      deterministic step (a round is already a pure function of prior state + command files),
      (3) optionally a pure step function over immutable state. **Not** ECS. The DTO seam means
      none of this is visible to the UI.

- Decided against: making each `Command` declare its own execution phase. The switch in
  `CommandSet.add` keeps all the tick ordering visible in one place, which is what makes it easy
  to move a command between phases while debugging.

## Application services (`../arena/app`)

- [ ] **`inspect` from the shell.** `AdminService.stale_rounds` already reports, per round, what a
      saved world names that the code no longer has. A CLI action over it answers the same
      question when the console will not start, which is exactly when it is wanted.

- [ ] **`_EngineAccess` is a shared-behaviour base wearing an access name.** It holds `_gd` and
      `list_games`, which is what the name promises, and then `settings`, `save_settings`,
      `all_ready`, `is_ready`, `set_ready`, `pulse`, `games_for_player` and `_roster`, which are
      shared game operations. `_roster` now builds a `Game` to answer, so a class named for
      reaching files constructs an engine object. Either thin the base to file access and put the
      shared operations somewhere honest, or rename it for what it is.

## Documentation (`../docs`)

Written with the author, not handed over as a draft: the intent is human understanding *and*
stopping AI drift, and the reasoning is the part only a person can confirm.

    docs/README.md         what is here, and which file answers which question
    docs/architecture.md   the layers, what lives where, how a request and a round flow
    docs/glossary.md       round vs tick, faction, contact, commander, director, order
    docs/data.md           the game directory, the roster, commands, pickles, players.jsonl
    docs/deployment.md     the single WSGI app, the host's constraints, the build step
    docs/development.md    running, testing, regenerating, the two scripts
    docs/adr/NNNN-*.md     one decision each

ADRs are Nygard-style: **Context, Decision, Consequences, Alternatives rejected**. Numbered once
and never renumbered, and **edited whenever the decision moves**, because a record of a decision we
no longer take reads as current. **The rejected alternatives are the anti-drift payload**: "we use
DTOs" prevents nothing, "passing engine objects upward was rejected, and here is what it cost last
time" prevents the re-proposal.

- [ ] **`work` is outside the reference test, and rotted quietly.** `UNCHECKED` skips it because a
      to do list names what does not exist yet, which is right for symbols and wrong for
      everything else: this file carried four links that resolved nowhere from where they were
      written, and citations to lines that had moved. Check links and line numbers here even where
      symbols are not checked.

- [ ] **Nine citations still point at a line number**, all in
      [ADR 0019](../docs/adr/0019-machines-drive-components-through-one-vocabulary.md), listed by
      `python -m test.docs.test_references`. Convert them to a symbol or an anchor. Worth doing
      before anything else here: while that report always prints the same nine, nobody reads it,
      and the whole value is that it prints only what is new.

- [ ] **Split [ADR 0023](../docs/adr/0023-a-tick-advances-by-encounters.md).** It is two records
      fused, which is what the 0024 gap is, and it is larger than `architecture.md`. The decision
      stays; the sections explaining how the geometry works are a manual and belong in `../docs/`.
      Every reference that had rotted in this repo was in the explaining half of a record, because
      a rejected alternative stays rejected and an explanation does not.

- [ ] **One principle, three records.** [0004](../docs/adr/0004-components-own-their-parameters.md),
      [0010](../docs/adr/0010-objects-describe-themselves.md) and
      [0019](../docs/adr/0019-machines-drive-components-through-one-vocabulary.md) all say a thing
      answers for itself and nobody inspects its class. Needs a call before any editing: numbers
      are never reused or renumbered here, and there is no shape in that convention for
      consolidating three decisions that are all still taken. Parked until that is decided.

- [ ] **Generate `../docs/adr/README.md`** from the records rather than maintaining the table by
      hand, with a topic on each so the list groups instead of running flat. Kills a whole class of
      drift, and answers the real complaint: an append-only list with no structure is unreadable
      long before it is wrong. The ADRs and the GDDRs share one run of numbers and are counted by
      hand in two places today, which is the drift itself.

- [ ] **New ADRs as decisions come up.** Not a backlog to work through: write one when something is
      decided, especially when an alternative was rejected for a reason worth remembering.

- [ ] **A game's outcome does not reach Valhalla.** `outcome.json` says which side took a scenario
      game and what the objective paid, and the export carries neither, so a finished game in the
      museum still reads as combat score alone. Carrying it means a version of the schema, which is
      the decision to make first: [ADR 0034](../docs/adr/0034-a-finished-game-is-exported-to-a-schema-of-its-own.md).
      The same version would settle whether objective points belong in the standing or beside it.

## Making a game easily

- [ ] **Tooling for large rosters.** A row per ship stops scaling somewhere above twenty ships, and
      a full Five Faction War is five sides of twenty people flying up to three hulls each. The
      roster screen will render 300 rows; finding the one ship you want to rename is the problem.
      The assignment screen has the same shape at that size, and wants a "spread the rest" button
      that fills the columns in front of you rather than at submit time, so you can see what you
      got and move a few.
- [ ] **Relative power of the ship types.** A faction must not be handed the beginner hulls by
      accident. The table in `../arena/app/scenarios/five_faction_war.py` is where the answer lands,
      and possibly a per-faction ordering, so the first ship dealt to one side is comparable to
      the first ship dealt to every other. Note Insectoid has three hulls where the rest have four.
      Wants every type side by side: hull, shields per quadrant, speed, turn, delta-v, battery,
      generators, scan range, and what each launcher carries.
- [ ] **`Selector.svelte` still shows a raw game name** while it is loading one, when it has
      nothing to show for one, and in the planning header. The lists were fixed and these were
      missed, because `chooseGame` keeps the key rather than the `GameSummary` it came from.
- [ ] **A scenario cannot bring its own setup screen.** The assignment screen is generic across
      scenarios, which is right for anything shaped like factions and registrations. The first
      scenario that wants something else needs a way to say so; deriving a template name from the
      key was tried and thrown away as premature.

## Admin / director UI (`../arena/admin_ui`)

- [ ] **Scenario builder.** The long-term goal: world objects, NPCs, story beats, timed triggers,
      pick-ups, objective missions (protect a VIP, and so on). Grow it out of the admin UI,
      reusing the map and drag components from the game UI. The new-game screen's row editor is
      the start of its data model.

- [ ] **The console shows no solo games.** Deliberate so far. A read-only list with a delete is
      the cheap version if stale directories ever pile up.

## Hosting

Deployed on PythonAnywhere as a single WSGI app: `../arena/serve.py` serves the built UI as static
files from the root, mounts the Flask console under `/director` and sends `/api/...` to the
FastAPI app through `a2wsgi`. No Node at runtime; `npm run build --prefix game-ui` is a build step. Deploying is
`git pull` and a reload; every default in `../arena/cfg.py` is the deployed one and all paths are
anchored to the repository rather than the working directory.

**The host preforks with Python threads disabled.** uWSGI loads the app in a master process and
forks the workers, and a fork keeps only the calling thread, so anything with a background
thread, event loop or connection pool must be built on first use inside the worker, never at
import. `../arena/serve.py` builds the ASGI adapter that way; the symptom of getting it wrong is
every route timing out at `504-loadbalancer`.

- [ ] **Deploying the logins is order-sensitive.** The console refuses everyone until a director
      exists, so: `git pull`, then `./arena-link.sh <you> https://your.site --director` in a Bash
      console there, then open that link once. Deploy first and reload and you get the 403 page
      until you do - recoverable, but only through the shell.
- [ ] **Set `SITE_URL` in the host's `../secret.py`** (e.g.
      `SITE_URL = 'https://starship-arena-agfx.pythonanywhere.com'`) so `./arena-link.sh <name>`
      prints a whole link there without the address being typed each time. Left unset it prints a
      path, which is right for development where the address differs per runner.
- [ ] **Rebuild and commit `../game-ui/dist` whenever the UI changes**, tracked because the
      host has no build step. `npm run build --prefix game-ui`.
- [ ] **Consider dropping the CORS entry** in `../arena/api/app.py`. It exists only for the Vite dev
      server, but `../arena-dev.sh` proxies `/api` through Vite, so the browser is same-origin in
      development too.
- [ ] **Watch WeasyPrint.** It depends on system Pango/Cairo, and only the manual still needs it
      now that per-round PDFs are gone. If it breaks on the host, pin it back rather than
      chasing the latest.
- [ ] Local development stays on the latest Python (`.python-version` is 3.14); only the declared
      floor is 3.10. Worth compiling against the floor after language-level changes:
      `uv run --no-project --python 3.10 python -m compileall -q arena test`.
- [ ] Longer term, if the console should stay off the public internet, it can move to a separate
      deployment, but it would then need converting into a client of `/api/admin/*`, since today
      it calls the services layer **in-process** and reads game data from the filesystem.

## Testing / data

- [ ] **Encounter tests that should exist and do not.** A missile's last sighting agreeing with
      where its blast is; a ship bouncing and being caught in a blast in the same tick; a surface
      and a trigger at the same fraction resolving in one pass; and a wedge, where an object
      bounced off one surface into another spends the rest of the tick there.

      A wedge and the same-fraction case are unreachable in play today, because five rocks of
      radius 40 sitting 294 apart cannot wedge anything. That is exactly why the rule must not
      depend on the layout, and why the test has to build its own geometry rather than use a
      scenario.

      Two more, both about `Warhead.decide` and both written as the bugs above are fixed: a lasered
      missile dies without going off, and a blast that carries to another warhead carries whichever
      order the two are listed in. `test_a_blast_carries_to_the_missile_it_kills` covers the
      order-proof half already, because a proximity trigger resolves a phase earlier.

- [ ] **Half the console's routes are still untested.** The setup flow and the players page have
      tests now (`../test/admin_ui/test_scenarios.py`, `test_players.py`), which caught the roster
      screen offering the wrong players. Still only exercised by hand: `spawn`, `process_turn`,
      `force_process`, `regenerate`, the settings form and the game overview. The pattern is
      established: post the form, follow the redirect, assert on what came back.

      The game API has the same hole: `test/api/test_fastapimain.py` covers command validation,
      and the planning endpoint and the overview are only checked by hand.

- [ ] **The test suite writes into the committed test data.** `test_run_test_games.py` uses a
      cwd-relative `'./test/test-games'` and re-runs `setup_game()` on the real `test-game`, so
      running tests changes which round it is on. Should work on a copy.

      No longer the console's data root, at least: that moved to `game-data/`, so playing with a
      game can't take a fixture away from the suite any more.

- [ ] Game pickles are regenerable and gitignored: on schema drift, **delete them** rather than
      adding compatibility shims. Player orders live in `commands/*.txt` and are tracked, so they
      survive. The console's **Regenerate** button replays a game from its ships file and orders.

## Ideas

Maybe, later, or never. Nothing here is queued, nothing is promised, and an idea earning its place
means it moves up rather than growing in here.

- **Disabling as a thing a ship can suffer.** Ordnance dying quiet to a laser is a bug and is
      above; this is the rest of the idea. A hit that stops a component working rather than taking
      it apart wants `Component.status_effects` with `DISABLED` in it, on the component so parts go
      out one at a time. What a ship does with such a hit is the open question - disabling every
      component at once is not "lose a turret" - and the first effect that needs a duration stops
      being a marker and becomes instance state with a name. Reasoning in
      [plans/ship-balance-plan.md](plans/ship-balance-plan.md).
- **Point defence**, possibly as something an NPC gunner runs. A mount that is short-ranged on
      purpose, which the laser fix above is what makes possible.
- **Damage to individual components**, rather than only hull and shields.
- **Persistent wrecks.** A destroyed ship as an object in space rather than only a graveyard entry:
      something to scan, to shoot, to salvage, to hide behind. `Stance.Neutral` already means a
      factionless object triggers no warhead, so the minefield problem this used to have is gone.
      What it still wants is a radius on a ship, and a decision about whether a graveyard entry
      keeps the faction it has today.
- **Objects in space that are not machines.** Black holes, loot crates, whatever a scenario needs.
      `Body` proves the mechanism - a non-machine `ObjectInSpace` with a radius, answering
      `type_name` and `category_name` for itself - so a new kind is a registry entry rather than
      engine work. Waiting on something to want one.
- **Laser tweaks.** `heat_per_shot` is a class attribute, so every laser in the game fires 8 times
      a round; making it a constructor argument is what would let a duellist get 5 and a point
      defence mount 10. The starbase's two lasers are still on the placeholder reach with no arc,
      which suits a fortress badly. Every guided payload but the EMP still shares one airframe.
      All three are variety going unused and need no engine change.
- **A scanner that reveals internal detail** of a scanned ship: ammo, energy levels.
- **Utilities**, such as repair droids.
- **Message of the day**, and a message per round, the latter probably tied to a scenario.
- **Gas clouds and nebulae** alongside the solid bodies.
- **Leaderboard.** Per player: the last ten games and a lifetime total. A game's contribution is
      **total score divided by the number of ships they had in it**, so commanding a fleet is not
      worth more than commanding one ship well. `Event.score` is derived from the effects now, so
      what the points were for survives beside how many there were, which is the material this
      wants. Needs finished games first: a running game has no final score.
- **Fun statistics** alongside the score: kills, shields broken, ordnance fired, distance
      travelled. The history already records the events these come from; it is a question of what
      to count and where to keep the totals so it need not be recomputed from every round.
- **A player profile.** Storing a timezone per player buys nothing while a browser is in the room.
      It starts earning its place the day the server sends email on its own schedule, since nothing
      will be there to ask what "tomorrow morning" means for the person receiving it. That is also
      when the screen gets a second field to hold, and one field is a thin reason for a screen.
- **Four dead images in `../arena/admin_ui/static/gfx`.** `example-turn.png` and
      `command-interface.png` are the old UI; `starfield.jpg` and `astronaut.jpeg` went with the
      per-round PDFs. Nothing names any of them.