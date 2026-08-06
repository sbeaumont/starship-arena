# TODO

Running list of what is next and what is deliberately parked. Newest thinking at the top of
each section.

## Next, in order

1. **The leaderboard**, the last piece of player management still open.
2. **Ship balance**, before a Five Faction War is played for real. Assessed in
   [docs/ship-balance.md](docs/ship-balance.md), planned in
   [plans/ship-balance-plan.md](plans/ship-balance-plan.md). Steps 1 to 6 and 8 are done. What is
   left, in order: the Gunner, disabling, then the registry rewrite.
3. **Large objects**: solid bodies and crossing them (see Engine).
4. **Scenario builder**, now that a scenario is a real thing with a home.

## Game UI (`game-ui/`)

- [x] **Boost and Power have controls**, in the tick panel under the weapons. `ComponentStatus`
      now carries the collection the machine keeps a component in and the inputs an order to it
      needs, so the row that already showed shield strengths can be ordered from.

      The verb stayed out of the engine and out of the DTO. A component says what an order needs,
      never which order it is ([ADR 0004](docs/adr/0004-components-own-their-parameters.md)), and
      the selector already addresses it exactly, so nothing in the engine was missing. The browser
      maps `defense` to Boost and `ecm` to Power, which is the game's language a player types
      anyway. Reading a plan back matches on the selector rather than the verb, so a hand-written
      `B Shields W 50` keeps its spelling.

- [x] **Players are told when a round has been processed**, by polling `/pulse` every 20 seconds
      while the tab is visible. Push stays out on this host: SSE or a WebSocket holds a worker
      open, there are 2 of them, and harakiri kills a connection at 300 seconds anyway.
- [x] **Feedback after regenerating, processing and forcing.** The console redirects with a
      message and the game page shows it.
- [x] **Lock the path.** A button that freezes the plotted course, because setting weapon arcs or
      panning the map too easily drags a joint and changes a course that was already right.
- [x] **Ready / Not Ready, per player.** A flag saying "I am done with this round", distinct from
      having saved orders: you can save a plan and keep thinking about it.

      One file per player in the game directory, holding a `Round X Ready` line that gets added or
      removed. A file each, so two players marking ready at the same moment cannot race.

      Both things it was groundwork for are in: `process_on_all_ready` in a game's settings, and
      `arena-cron.sh` processing on the hours a game names, writing an empty command file for
      anyone who did not send one, which reads as "no orders arrived in time".
- [x] **Rename "Send all" to "Save all".** It saves orders; it does not send them anywhere. With
      Ready as a separate flag the distinction starts to matter.
- [ ] **Draw solid bodies.** Circles to start with, in muted colours: terrain should read as
      something to fly around rather than compete with contacts and blast circles for attention.
      A body's radius is a real distance, so it belongs in the world layer and scales with zoom,
      the way `plan.explosions` already draws with `r={e.radius}` and `stroke-width={cam.upp}`.
      More complicated shapes are coming (a large station, a boss), so the radius comes from the
      API and never from a constant in the browser, and the day a body stops being round it
      describes its own outline rather than the map learning a list of them.
      Bodies are terrain and probably public (see Engine), so they are not contacts built from
      scans and want their own collection on `PlayerPlan`, present every round whether anything
      scanned them or not.
- [ ] **A new manual.** `manual.html` describes the old UI and is out of date throughout, so it
      wants rewriting rather than correcting. Decide whether it stays a PDF or becomes a page in
      the game UI.

      Two parts of it should not be prose at all. The order language is written down in
      [docs/orders.md](docs/orders.md) and the verbs are in `COMMAND_WORDS`, so the command
      reference can be generated the way the ships reference already is. What is left is the
      part that has to be written: what a round is, how planning works, and what wins a fight.
- [ ] **Time-scrubbing within a round.** Round-by-round works; stepping tick by tick does not.
      Snapshots now hold per-tick component state as well as position, so a slider over
      `TickState` would show shields dropping and ammo going down, not just movement.
- [ ] **Visualise a ship kill.** A destroyed ship simply stops appearing: it drops out of the
      status file and its track ends. Blast circles are drawn already, but nothing marks *this is
      where something died*. The graveyard holds destroyed player ships, and the killing blow is
      in the witnesses' histories as a `HitEvent`.
- [ ] **You lose sight of your own ordnance.** Contacts are built purely from scans, so a rocket
      you fired drops off the map once it outruns your scan range: an H2545 sees 180 and its own
      rocket is past that by tick 4. Your own ships are already treated as ground truth rather
      than fog of war (`allies are ground truth` in `get_player_plan`); the argument for ordnance
      is the same. Decide whether it is everything you own or only what is still flying.
- [ ] **Spectator view.** Whole game, tick by tick, with short tails (about three ticks) instead
      of a full round's trail. Wants a player-less view keyed on the game rather than a player.
- [ ] **Replenish has no control.** It addresses the ship rather than a component, so it takes
      neither a selector nor parameters and none of the component machinery fits it. It belongs
      with turn and throttle, not in the tick panel's component list.
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
      [docs/information.md](docs/information.md) and the same defect as
      `MineType.max_scan_distance`. So decide where the number lives before adding the DTO field.
- [ ] **Laser with no resolvable target** draws a 20-unit stub instead of a beam. Harmless now
      (a target is always picked from the map) but wrong if an order survives its target.
- [ ] **Per-ship standing orders** for `Pilot`/`Gunner` once those are live: a target and a
      Defensive/Offensive mode are per-ship settings, not per-tick commands, so they belong in a
      ship panel rather than on a tick.

## Engine

- [ ] **A Gunner, and the Engage standing order.** Lasers are unaimable, not weak. Orders are
      plotted ten ticks ahead against a captain choosing their own course, so nobody can know they
      will be 15 units away on tick 7. A missile forgives a bad prediction because it steers; a
      laser does not. Steep falloff was tried before and the fix was to raise the numbers, which
      is how one number came to mean both damage and reach.

      The answer is a crewman. A `Gunner` acts in `decide`, after everything has scanned, so it
      fires on where things actually are. `Engage <gunner> <weapon> <target> <within> <shots>`
      holds until changed, and the player's job becomes positioning rather than tick-prediction.

      `Gunner` and `Pilot` exist and no ship type carries either: `control` is empty everywhere.
      Three things to fix on the way. It queues for `tick.tick + 1`, which reintroduces the lag
      this is meant to remove. And it has both ADR 0019 violations that ADR names: `isinstance`
      to find its lasers, and `isinstance` to sort targets, where `category_name` already answers
      the second.

      Open: whether the gunner holds one engagement or one per gun. One per gunner makes the
      number of fire-control stations a hull stat, which is free variety.

- [ ] **A disabling hit.** A hit either takes something apart or stops it working.
      `Component.status_effects`, a set, with `DISABLED` its first member. On the component so
      parts go out one at a time, mirroring `ObjectInSpace.tags`. Not `conditions`:
      `TickCondition` already means a ship's readouts and the UI renders it as `hull 90 · bat 40`.

      `DamageType.Laser` exists now, so ordnance can answer a laser hit by disabling itself as
      well as dying, and its warhead does not fire. A ship answers the same hit as plain damage.
      Nothing models "disabling" as a kind of harm: it is what a missile decides a laser means.
      Disabled ordnance disappears rather than drifting, because clutter costs more than the fog
      of war would buy.

      This is what lets point defence be short-ranged. Hits land simultaneously and kills resolve
      at the end of a tick, so shooting a missile in the tick it detonates does not stop it.
      Without disabling an intercept must happen a tick early, which puts a floor of 40 to 80
      under a defensive mount and makes it the longest gun on the ship.

      Costs: detonation has to leave `decide` for a resolution pass, following
      `GameRound.detect_collision`'s detect-then-apply shape, and that pass must loop or chain
      detonation stops at one link. No duration on effects yet; the first that needs one is EMP
      disabling a ship's components, and a duration is a value, so it stops being a marker.
      Reasoning in [plans/ship-balance-plan.md](plans/ship-balance-plan.md).

- [ ] **`number_of_inputs` is dead machinery.** `BoostQuadrantParameter` was the only parameter
      consuming more than one word, and splitting it into a quadrant and an amount removed the
      last user. Four lines in `ComponentCommand._init_params` and a property on `Parameter` now
      serve a case that cannot arise. Delete, or keep deliberately as an extension point.

- [ ] **Large objects, and crossing them.** Solid bodies with a radius, and movement that notices
      them. A tick is a teleport: `move()` translates the whole speed at once, so nothing between
      the endpoints exists. The primitive already exists: `ObjectInSpace.approach_fraction` answers
      how far into the tick two legs first closed to a given distance, which is a body's surface,
      and `position_at` turns that back into a point. Warheads ask the other question,
      `closest_fraction`, because a proximity fuse wants the shortest gap rather than the first
      contact.
      What a hit does is settled in [ADR 0023](docs/adr/0023-a-collision-transmits-an-impulse.md):
      a collision transmits an impulse and the object receiving it decides. Static bodies first:
      everything moves in one loop, so ship-versus-ship collision would depend on iteration order.
      Still open: whether bodies are public knowledge (probably - terrain, not fog of war), and
      where they are placed (`bodies.txt` until the scenario builder owns world objects). Gravity
      is a different feature; park it.
- [ ] **Solid bodies block line of sight.** Deliberately left out of ADR 0023 so the first cut
      stays movement only. A planet you can shoot straight through is wrong, and hiding behind one
      is worth having. Touches scanning, lasers and the blast loop in `Warhead.explode`, and the
      game UI has to draw the shadow or players cannot plan around it.
- [ ] **Processing order must not affect the outcome, and today it can.** Weapons fire in the
      post-move phase, so a missile launched this tick may or may not already be "in space" when
      something explodes, depending on where its launcher sat in the iteration. The common symptom:
      every rocket a ship just fired blows up when that ship is hit in the same tick. Possible
      fixes: fire pre-move, or let weapons fire only after existing objects have exploded. The game
      is built on the premise that iteration order never matters, so this is a real defect rather
      than a quirk.
- [ ] **`leaves_a_wreck` may need to be settable per ship.** It is a model constant on `ShipType`
      today, so every ship and starbase leaves a graveyard entry and no model can differ. A swarm
      of throwaway NPC hulls would want to opt out without becoming a new ship type. That means
      moving it to instance state in `Ship.__init__` and overriding the derived answer, which is
      an internal change: readers already ask the machine, and it crosses no seam. See
      [docs/information.md](docs/information.md).
- [ ] **A malformed Boost command crashes.** Long-standing.
- [x] **The CLI could not take an action and a game name.** `action` was `nargs="*"` ahead of an
      optional `gamedir`, so argparse handed both words to `action` and every documented form
      exited with `invalid choice`. One action per call now, which is the only shape that parses;
      running `setup generate <game>` in one go goes with it, and nothing documented did that.
- [ ] **`setup_game` before `regenerate_game` replays nothing.** Setup cleans the pickles, so
      `regenerate_game` then reads its target round as 0 and stops. Only bites a script that calls
      both; worth a line in `regenerate_game`'s docstring, or having it take the target round.
- [ ] **Damage to individual components**, rather than only hull and shields.
- [x] **In-game spawning, and respawning after death.** Two ways in: the director schedules one
      into a round through the console, which lands in `spawns.jsonl`; or a starbase's
      `ShipSpawner` rebuilds a wreck with `Fire SS <wreck> <direction>`, three times a game.
      Whichever creates it, the object arrives through `World.spawn(tick)`.

      What it opens up: a carrier's hangar is the same component with a different source for what
      it may put out, and a scenario trigger is a third writer of the spawn plan.
- [x] **A wreck is claimed once.** A `claimed` tag on the wreck rather than a field: too small a
      fact to earn one. `ObjectInSpace.tags` is a set of strings, the well-known ones defined next
      to the rule that sets them. See [docs/information.md](docs/information.md) for the line a tag
      must not cross.

      It also gave the planning UI its dropdown: `World.find_objects` takes where, tags and
      faction, so an order can offer "our unclaimed wrecks" without anything above the engine
      knowing what those words mean.
- [ ] **Objects in space that are not machines.** Black holes, asteroids, loot crates, and
      whatever a scenario needs to put in the world. `ObjectInSpace` is already the base for
      "anything in space" rather than "anything built", and `type_name` / `category_name` are
      abstract, so a new kind answers for itself and the map keys its blip off the category
      without being told. Needed by the scenario builder.
- [ ] **Wrecks that stay on the battlefield.** A destroyed ship as an object in space rather than
      only a graveyard entry: something to scan, to shoot, to salvage, to hide behind. Belongs with
      the entry above, and it collects prerequisites. A wreck has no faction, and
      `Warhead.triggers_on` goes off on anything factionless, so every wreck would be a minefield.
      It also wants the large-objects work, to have a radius.
- [ ] **`Ship.fire` and the `Commandable` protocol have to go together.** `Ship.fire`
      (`ship.py:98`) is called by nothing: `FireCommand` resolves the component through the
      selector and calls it directly. But `Commandable` is `runtime_checkable`, so deleting the
      method alone makes `isinstance(ship, Commandable)` false and every ship's orders are skipped
      in silence. The method and the protocol member go, or neither does. See
      [ADR 0019](docs/adr/0019-machines-drive-components-through-one-vocabulary.md) on why a
      protocol is the wrong shape here.
- [ ] **`MineType.max_scan_distance` asks the type, not the mine** (`registry/mines.py:18`). It
      reads `self.weapons[0].range`, which builds a throwaway warhead to get a number off it and
      then takes whichever happens to be first, so a `NanocyteMine` reports its Splinter's 6 rather
      than its Nanocyte's 50. `MachineInSpace.range` already answers this on the instance. Fixing
      it moves scan ranges and therefore outcomes.
- [ ] **Parameter naming says the opposite of what it means.** `ComponentParameter` means "a
      parameter belonging to a component", while `ComponentSelectorParameter`, whose value *is* a
      component, subclasses `Parameter` directly.
- [ ] **Separate history from the entities.** `ObjectInSpace` is both the live object and its own
      per-tick archivist. Staged plan: (1) pull the recorder/timeline out of the entity,
      (2) if replay and scenarios become central, make the timeline *derivable* by re-running the
      deterministic step (a round is already a pure function of prior state + command files),
      (3) optionally a pure step function over immutable state. **Not** ECS. The DTO seam means
      none of this is visible to the UI.
- [ ] **NPC controllers build commands from text.** `Pilot`/`Gunner` format a string and hand it
      to the parser. If they go live, construct `Command` objects directly and add
      `Command.as_text()` for reports and logs. Validation lives in `Command.__init__` /
      `Parameter.is_valid`, not in the parsing, so nothing is lost.
- [ ] **A duplicate order for one weapon in one tick disappears silently.** Two `Fire R1 90`
      lines on the same tick produce one shot with no feedback, which is what made
      `test_run_test_games_2` wrong for a long time. Everywhere else a refused command records an
      `InternalEvent`; this should too.
- [ ] **`Vector` and `Point` are mutable, so the heading guarantee has a hole.**
      `Vector.__post_init__` folds a heading into [0, 360), which covers construction and
      everything built through `replace`: `turn`, `move`, `translate`, `accelerate`. Assigning a
      field in place skips it, which is why `Ship.turn` (`ship.py:120`) still needs its own
      `% 360`. Freezing both dataclasses would close it and put every change through one door.
      Touches `mine.py:52`, `ship.py:93,120` and `missile.py:114`. Note `Ship.turn` normalises the
      *rounded* heading where `Vector.turn` uses the raw float, so consolidating the two shifts
      ship headings by fractions of a degree and moves every replay outcome.
- [ ] **Five places name a component instead of asking all of them**, against
      [ADR 0019](docs/adr/0019-machines-drive-components-through-one-vocabulary.md). Each is a spot
      where a new component is silently ignored, so they block the healer, the teleporter and the
      spawner-in-a-missile as much as they are wrong today.
      - `Missile.decide` calls `self.warhead.decide(...)` (`missile.py:59`) through a property that
        looks up the literal key `'warhead'` (`missile.py:39`, `mine.py:28`). A missile with two
        components only ever runs one. `Mine.decide` loops and is right; copy that.
      - `BoostCommand._init_params` finds its shield with `isinstance(d, Shields)`
        (`command.py:224`). Asking each defense component for a `boost` parameter would do it.
      - `Gunner.lasers` filters `isinstance(weapon, Laser)` (`control.py:99`) so an NPC gunner can
        fire nothing else, and `Gunner.decide` sorts targets with `isinstance(enemy, (Missile,
        Mine))` (`control.py:82`). The second wants a question on the object, not its class.
      - `Ship.take_damage_from` guards with `hasattr(self, 'outer_defense')` (`ship.py:143`), which
        is always true: `outer_defense` is a property on the class (`ship.py:58`). Dead guard.
      - `Warhead.explode` reads `ois._type.max_scan_distance` (`warhead.py:49`, `:67`), through
        another object's type and past a private attribute.
- Decided against: making each `Command` declare its own execution phase. The switch in
  `CommandSet.add` keeps all the tick ordering visible in one place, which is what makes it easy
  to move a command between phases while debugging.

## Application services (`arena/app/`)

- [ ] **`_EngineAccess` is a shared-behaviour base wearing an access name.** It holds `_gd`,
      `list_games` and `_archive`, which is what the name promises, and then `settings`,
      `save_settings`, `all_ready`, `is_ready`, `set_ready`, `pulse`, `games_for_player` and
      `_roster`, which are shared game operations. `_roster` now builds a `Game` to answer, so a
      class named for reaching files constructs an engine object. Either thin the base to file
      access and put the shared operations somewhere honest, or rename it for what it is.

## Documentation (`docs/`)

Written with the author, not handed over as a draft: the intent is human understanding *and*
stopping AI drift, and the reasoning is the part only a person can confirm.

    docs/README.md         what is here, and which file answers which question
    docs/architecture.md   the layers, what lives where, how a request and a round flow
    docs/glossary.md       round vs tick, faction, contact, commander, director, order
    docs/data.md           the game directory, the roster, commands, pickles, players.jsonl
    docs/deployment.md     the single WSGI app, the host's constraints, the build step
    docs/development.md    running, testing, regenerating, the two scripts
    docs/adr/NNNN-*.md     one decision each

ADRs are Nygard-style: **Context, Decision, Consequences, Alternatives rejected**, with a status
of Accepted or Superseded by NNNN. Numbered once, never renumbered, never edited after acceptance
- a change is a new ADR that supersedes the old. **The rejected alternatives are the anti-drift
payload**: "we use DTOs" prevents nothing, "passing engine objects upward was rejected, and here
is what it cost last time" prevents the re-proposal.

- [x] **18 ADRs written**, covering the layering, determinism, type objects, components,
      commands, file storage, the single WSGI app, laziness and statelessness, anchored paths,
      self-describing objects, snapshots, open information, fog of war, logins, Svelte, the URL as
      state, the two SVG layers and jointed-chain planning.
- [ ] **New ADRs as decisions come up.** Not a backlog to work through: write one when something is
      decided, especially when an alternative was rejected for a reason worth remembering.
- [x] **`CLAUDE.md` folded back** to constraints plus commands, with per-directory files for
      `arena/engine`, `arena/app`, `arena/api`, `arena/admin_ui` and `game-ui`.
- [x] **`readme.md` rewritten** as the front door: what the game is, how to run it, what is worth
      knowing before reading the code, and where the rest lives. Its old backlog was migrated into
      this file first, including the processing-order defect and the Boost crash.
- [x] **Mermaid diagrams**: the layers and the tick phases in `architecture.md`, the request
      switchboard and dev-versus-deployed in `deployment.md`.

## Documentation, continued

- [x] **Documentation meta-rules extracted into a skill**:
      `.claude/skills/project-documentation/`, with copyable templates. `share/ai-guardrails/`
      is the same thing packaged for someone on another agent, prose rules included.

- [ ] **Close the console's engine imports.** `arena/admin_ui` reaches into `arena/engine` in five
      places, which `docs/architecture.md` rule 3 forbids: the console is a user interface and
      goes through `AdminService`. `AppFacade` builds `Game` objects directly today. Doing this
      also makes the later move of the console onto `/api/admin/*` possible.

## Game features

Ideas from the original readme, kept because they are still wanted.

- [ ] **The registry rewrite: arcs, and what each race is for.** Two thirds of the fleet's weapons
      and 64% of its round damage sit on 360 degree arcs, and only three widths exist in the whole
      registry. Narrowing them is the largest source of variety available, and it makes `max_turn`
      decide fights: bringing a 30 degree arc to bear is 9 ticks for a Swarm and 4 for a Tiger.

      The races are settled. Reptilian ambushes with the best cloak and lasers as the alpha
      strike, and lays no mines. Feline raids, fast and agile, cloaked but less so, carrying a few
      mines to place. Insectoid holds ground with broadsides and fields, because at 20 to 30 turn
      it cannot have narrow arcs at all. Human does attrition, owning EMP and nanocyte mines.
      Amphibian is standoff, which needs the payload airframe to vary: every missile in the game
      currently dies at 900 units. Every hull keeps a mine tube and a rocket tube.

      Placeholder values to replace, all uniform where they should differ: every laser on reach
      60, every cloak on `half_power` 4 where Reptilian wants 3 and Feline 6, and `heat_per_shot`
      a class attribute so every laser in the game fires 8 times a round.

      Wants an `arc(centre, width)` helper next to `in_firing_arc`, so a broadside reads as
      `arc(90, 60)` rather than `(60, 120)`. Do it after the Gunner: how hard a laser hits can
      only be judged once it is known how often it gets to hit at all.
      Detail in [plans/ship-balance-plan.md](plans/ship-balance-plan.md).

- [ ] **See explosions from far away, or from anywhere.** You would know where the fighting is
      without knowing what is in it, which gives a fleet a reason to move toward something and
      makes a big map feel occupied rather than empty.

      Today an explosion is handed to whatever is close enough to scan it (`Warhead.explode`
      checks `distance_to(pos) <= max_scan_distance`), so a battle two scan ranges away is
      invisible. Loosening that is a change to what fog of war means, so it wants a decision
      alongside [ADR 0013](docs/adr/0013-fog-of-war-from-scans.md) rather than a quiet edit.

      What to settle: whether it is truly global or just a much longer range, and whether a
      distant blast is degraded to a position and nothing else. `ExplosionEvent` carries its
      source, damage type and radius, so shown as-is it would tell you what kind of warhead went
      off and roughly whose it was. Hits stay scan-gated either way: seeing a flash is the point,
      reading the battle is not.

- [ ] **A scanner that reveals internal detail** of a scanned ship: ammo, energy levels.
- [ ] **Point defence**, possibly as something an NPC gunner runs.
- [ ] **Utilities**, such as repair droids.
- [ ] **Message of the day**, and a message per round, the latter probably tied to a scenario.
- [ ] **Gas clouds and nebulae** alongside the solid bodies, once objects in space exist.

## Player management

The lists grow without bound as games pile up, so this is about keeping them maintainable.

- [x] **Archive a game.** An archived game is no longer referenced anywhere: not in the console's
      list, not in a player's games, not in the roster that decides whether a name is claimable.
      Its data stays. It moves to an `archived` directory beside the games, so nothing that lists
      games has to filter and `archived` stays a legal game name.
- [x] **Unarchive**, and **delete an archived game for good** - deletion only from archived, so it
      is always two deliberate steps.
- [x] **Deactivate a player.** The name stays reserved (nobody else can claim it, and old games
      keep naming them), but they cannot log in and are not offered when setting up a new game.
      Distinct from revoking a link, which only takes away the current token. An `Active` column
      in `players.jsonl`, and `by_token` refusing them, which closes every interface at once.
- [ ] **Leaderboard.** Per player: the last ten games and a lifetime total. A game's contribution
      is **total score divided by the number of ships they had in it**, so commanding a fleet is
      not worth more than commanding one ship well.
- [ ] **Fun statistics** alongside the score: kills, shields broken, ordnance fired, distance
      travelled. The history already records the events these come from; it is a question of what
      to count and where to keep the totals so it need not be recomputed from every round.

## Making a game easily

- [x] **Deal players into a game.** Drag registrations into faction columns, and whoever is left
      is spread at random to even the numbers. `arena/app/scenarios/`, screens at `/new_game`,
      `/registering` and `/registering/<game>`. See
      [plans/scenario-setup-plan.md](plans/scenario-setup-plan.md).
- [x] **A sign-up page.** The director names a game and opens it, players put themselves down in
      the game UI with a name per ship, and the console deals them into factions by dragging. A
      game being formed is a game directory in `registering/`, and starting it moves the directory
      into play.
- [x] **Predefined factions.** The Five Faction War brings its own: five of them, each with its own
      line of hulls, every active one carrying a starbase that one of its players commands. The
      engine knows nothing about any of it; a scenario is what says which hulls a faction flies.
- [x] **More than one ship.** Up to what the scenario allows, asked for at sign-up by naming that
      many ships. The dealer levels the factions against each other, so a faction is never
      outgunned by who happened to ask for three, and nobody is promised a ship they lose later.
- [ ] **Tooling for large rosters.** A row per ship stops scaling somewhere above twenty ships, and
      a full Five Faction War is five sides of twenty people flying up to three hulls each. The
      roster screen will render 300 rows; finding the one ship you want to rename is the problem.
      The assignment screen has the same shape at that size, and wants a "spread the rest" button
      that fills the columns in front of you rather than at submit time, so you can see what you
      got and move a few.
- [ ] **Relative power of the ship types.** A faction must not be handed the beginner hulls by
      accident. The table in `arena/app/scenarios/five_faction_war.py` is where the answer lands,
      and possibly a per-faction ordering, so the first ship dealt to one side is comparable to
      the first ship dealt to every other. Note Insectoid has three hulls where the rest have four.
      Wants every type side by side: hull, shields per quadrant, speed, turn, delta-v, battery,
      generators, scan range, and what each launcher carries.
- [ ] **The game UI still shows raw game names.** `display` is already on the DTOs it fetches, so
      this is reading a different field in `Selector.svelte` and `OpenGames.svelte`.
- [ ] **A scenario cannot bring its own setup screen.** The assignment screen is generic across
      scenarios, which is right for anything shaped like factions and registrations. The first
      scenario that wants something else needs a way to say so; deriving a template name from the
      key was tried and thrown away as premature.

## Admin / director UI (`arena/admin_ui/`)

- [x] **The game page keeps up by itself**, polling `/game_status/<game>` every 15 seconds for who
      has handed in and who has said ready. It costs no round load. When the round has moved on
      the whole page is stale, so it reloads.

- [ ] **Scenario builder.** The long-term goal: world objects, NPCs, story beats, timed triggers,
      pick-ups, objective missions (protect a VIP, and so on). Grow it out of the admin UI,
      reusing the map and drag components from the game UI. The new-game screen's row editor is
      the start of its data model.

## Hosting

Deployed on PythonAnywhere as a single WSGI app: `arena/serve.py` serves the built UI as static
files from the root, mounts the Flask console under `/director` and sends `/api/...` to the
FastAPI app through `a2wsgi`. No Node at runtime; `npm run build --prefix game-ui` is a build step. Deploying is
`git pull` and a reload; every default in `arena/cfg.py` is the deployed one and all paths are
anchored to the repository rather than the working directory.

**The host preforks with Python threads disabled.** uWSGI loads the app in a master process and
forks the workers, and a fork keeps only the calling thread, so anything with a background
thread, event loop or connection pool must be built on first use inside the worker, never at
import. `arena/serve.py` builds the ASGI adapter that way; the symptom of getting it wrong is
every route timing out at `504-loadbalancer`.

- [ ] **Deploying the logins is order-sensitive.** The console refuses everyone until a director
      exists, so: `git pull`, then `./arena-link.sh <you> https://your.site --director` in a Bash
      console there, then open that link once. Deploy first and reload and you get the 403 page
      until you do - recoverable, but only through the shell.
- [ ] **Set `SITE_URL` in the host's `secret.py`** (e.g.
      `SITE_URL = 'https://starship-arena-agfx.pythonanywhere.com'`) so `./arena-link.sh <name>`
      prints a whole link there without the address being typed each time. Left unset it prints a
      path, which is right for development where the address differs per runner.
- [ ] **Rebuild and commit `game-ui/dist` whenever the UI changes**, tracked because the
      host has no build step. `npm run build --prefix game-ui`.
- [ ] **Consider dropping the CORS entry** in `arena/api/app.py`. It exists only for the Vite dev
      server, but `arena-dev.sh` proxies `/api` through Vite, so the browser is same-origin in
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

- [ ] **Half the console's routes are still untested.** The setup flow and the players page have
      tests now (`test/admin_ui/test_scenarios.py`, `test_players.py`), which caught the roster
      screen offering the wrong players. Still only exercised by hand: `spawn`, `process_turn`,
      `force_process`, `regenerate`, the settings form and the game overview. The pattern is
      established: post the form, follow the redirect, assert on what came back.

      The game API has the same hole: `test/api/test_fastapimain.py` covers command validation,
      and the planning endpoint and the overview are only checked by hand.

- [ ] **The test suite writes into the committed test data.** `test_run_test_games.py` uses a
      cwd-relative `'./test/test-games'` and re-runs `setup_game()` on the real `test-game`, so
      running tests changes which round it is on. Should work on a copy.

      The same data root is what the console runs on, so archiving a game there takes it away from
      the suite: `test/api/test_fastapimain.py` copies its fixture out of `test-games/apitest`,
      and with that game archived three tests error on a missing directory.
- [ ] **`test_distribute_ships` is flaky.** It asserts no placed ship has an x or y of exactly
      zero, but `centers_for` places them at a random angle, which occasionally rounds to it.
      Seen twice; 20 runs since have been clean.
- [ ] Game pickles are regenerable and gitignored: on schema drift, **delete them** rather than
      adding compatibility shims. Player orders live in `commands/*.txt` and are tracked, so they
      survive. The console's **Regenerate** button replays a game from its ships file and orders.
