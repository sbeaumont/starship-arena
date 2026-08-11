# TODO

Running list of what is next and what is deliberately parked. Newest thinking at the top of
each section.

## Next, in order

1. **A pass over the ship registry**, to give the hulls an identity worth choosing between. Runs
   on the tools that exist. Assessed in [docs/ship-balance.md](../docs/ship-balance.md), planned in
   [plans/ship-balance-plan.md](plans/ship-balance-plan.md), where steps 1 to 6 and 8 are done.
2. **The Gunner and the Engage order**, then **a disabling hit**, which is what makes a laser
   worth aiming and point defence worth carrying. A second registry pass follows if they move the
   laser numbers.
3. **The leaderboard**, the last piece of player management still open.
4. **Scenario builder**, now that a scenario is a real thing with a home.

## Game UI (`../game-ui`)

- [x] **A solo game, so a new player has something to fly.** They pick one or two hulls, and get
      the standard five asteroids, three drifting pirate hulls and a game that processes the
      moment they say they are ready. One per player, in `solo-games/` beside the other three
      roots, named `Solo_<player>`.
      [ADR 0030](../docs/adr/0030-solo-games-live-in-their-own-root.md).

      Almost none of it was new. `GamesRoot.holding` resolves which playable root a game is in, so
      the map, the orders, the ready flag, the pulse and the journal all worked on it unchanged,
      and `process_on_all_ready` already meant one player pressing Ready runs the round. What was
      added is the scenario, two API routes and a page.

      Still open, in the order they will start to itch:
      **the pirates fly nothing.** They drift, get scanned and get shot, and nothing shoots back.
      This is the first real customer for `Pilot` and `Gunner`, below.
      **No objectives, and no way to finish.** A solo game runs until the player stops caring.
      Wants scenario triggers, which is the same machinery the story scenarios want.
      **Nothing teaches.** The manual is a PDF behind a menu; the map explains itself to nobody.
      A first round with something pointing at the controls is the actual tutorial.
      **The console shows none of them.** Deliberate for now. A read-only list with a delete is
      the cheap version if stale directories ever pile up.

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
- [x] **Draw solid bodies.** Muted circles in the world layer, under everything else, so terrain
      reads as something to fly around rather than competing with contacts and blast circles.

      Two things went differently from the sketch here. A body is **scanned like anything else**,
      so it is an ordinary `Contact` and needs no collection of its own on `PlayerPlan`; fog of war
      applies to terrain the way it applies to ships. And the map **keys off the radius**, not off
      a category name, so the day a body stops being round it describes its own outline and nothing
      in the browser has learned a list of shapes. `Contact.friendly` became `Contact.stance` on the
      way, because a bool could only say mine or theirs and a rock came out as theirs.
- [x] **A new manual.** `manual.html` described the old UI and was wrong throughout, so it was
      rewritten rather than corrected. It stays a PDF: the ship tables were already reflection
      over the registry, and that is the half that goes stale on its own.

      Every rule in it was checked against the engine rather than against the old text. The ones
      that had drifted furthest: hull scored 2 a point and scores 1, the laser was
      `strength - distance` and is now squared falloff over damage and reach, the gravscan reached
      6000 and reaches 1200, the cloak was a 20% on/off switch and is a power draw on a halving
      curve, and the standstill free-turn is gone. Mines, terrain, firing arcs and fog of war were
      missing entirely.

      It describes **actions, not a language**. A player never types an order, so the manual names
      Fire, Boost, Power and Replenish rather than teaching `<tick>: <verb>`, aliases and comment
      lines. What that costs: nothing tells a player what the log means when it quotes the order
      that ran. Worth a line if anyone asks.

      Illustrated with one shot, `static/gfx/game_ui.png`, which carries all three parts at once:
      log, map with a selected joint, and that tick's order buttons. The image and its caption are
      separate paragraphs because the shared `img` rule has no bottom margin and the caption
      otherwise sits on the picture.

      Four images in `static/gfx/` are now dead: `example-turn.png` and `command-interface.png`
      are the old UI, `starfield.jpg` and `astronaut.jpeg` went with the per-round PDFs. Nothing
      outside this file names any of them.

- [x] **Friendly fire scored.** `HitEvent.can_score` compared factions with `is not`, and two
      ships whose faction came off separate lines of `ships.jsonl` hold equal strings that are not
      the same object. It answered True, so you scored for hitting your own faction. Now `!=`.
- [x] **A gravscan's strength did nothing.** It was set to 100 in `__init__`, read only by
      `description`, and reach came off a hardcoded `max_scan(200)`. Strength is now the scan
      rating that `max_scan` multiplies, the same shape as a hull's, and `max_scan_distance` is
      derived from it. Default 200, so every reach is exactly what it was: 1200 at a 30 degree
      cone, 346 at 360.

      It's a constructor argument now, the way `Laser`'s damage and reach are, so hulls can differ.
      They all still take the default. **Varying it is a balance decision**, and
      [docs/ship-balance.md](docs/ship-balance.md) already lists the identical gravscan on all 20
      objects as sameyness worth spending.

      Saved rounds from before this hold `strength = 100`, and the new property reads it rather
      than the baked-in distance, so an old pickle scans 600 instead of 1200. Regenerate.
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
      Three things to fix on the way. It queues for `tick.tick + 1`, which reintroduces the lag
      this is meant to remove. And it has both ADR 0019 violations that ADR names: `isinstance`
      to find its lasers, and `isinstance` to sort targets, where `category_name` already answers
      the second. `Laser.can_fire_at` also has to start checking `in_firing_arc`.

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

- [x] **Large objects, and crossing them.** Solid bodies with a radius, and movement that notices
      them. A collision transmits an impulse and the object receiving it decides what that means
      ([ADR 0023](../docs/adr/0023-a-tick-advances-by-encounters.md)), and a tick advances by
      resolving encounters rather than teleporting from endpoint to endpoint
      ([ADR 0023](../docs/adr/0023-a-tick-advances-by-encounters.md)). Terrain is public: a body is
      scanned like anything else and a `Contact` carries a `stance` and a `radius`, so the map
      keys off the size rather than off a category name. Placed from `bodies.jsonl`, written by
      the scenario.

      Still open: ship against ship, which needs the processing-order defect below fixed first.
      Gravity is a different feature; parked.
- [ ] **Does a wreck bounce?** A graveyard entry is not in `world.objects`, so it never collides.
      Fine for now, and slightly odd once a wreck is drifting somewhere a player can see it.
- [ ] **A respawn placed inside a body is nobody's decision.** Nothing checks where
      `ShipSpawner` puts a ship. One overlapping an asteroid is found in contact on its first move
      with a leg and bounced out, which is probably right by accident rather than by rule.
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
      [docs/information.md](../docs/information.md).
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
      to the rule that sets them. See [docs/information.md](../docs/information.md) for the line a tag
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
- [x] **`Ship.fire` and `Ship.activation` are gone, with their protocol members.** Both were dead
      once the activation command reached its component directly. They could not go one at a time:
      `Commandable` is `runtime_checkable`, so removing a method without its protocol entry makes
      `isinstance(ship, Commandable)` false and every ship silently takes no orders.
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
- [ ] **Four places name a component instead of asking all of them.** Each is a spot where a new
      component is silently ignored, so they block the healer, the teleporter and the
      spawner-in-a-missile as much as they are wrong today. The list, with line numbers, is in
      [ADR 0019](../docs/adr/0019-machines-drive-components-through-one-vocabulary.md) under *Where
      the code does not do this yet*. Two of them are in `Gunner` and go with that work.
- Decided against: making each `Command` declare its own execution phase. The switch in
  `CommandSet.add` keeps all the tick ordering visible in one place, which is what makes it easy
  to move a command between phases while debugging.

- [x] **Damage travels inwards, and every layer answers the same way.** A component that takes
      damage returns an `Effect`: which layer, `Unaffected`/`Damaged`/`Breached`, what it took,
      what that was worth, and what carried on. The machine is the last layer and answers in the
      same words, where `Breached` on the hull is the kill.

      A shield is now handed only the damage type, the amount and the direction, so it cannot read
      the blow, cannot know whose it was, and cannot write a sentence about whoever fired. That is
      what pulled the phrasing out of the components: `HitEvent.__str__` composes one line from the
      symbols, and an interface can take that over one event at a time.

      Three defects went with it. Damage did not actually propagate: each component read
      `hit_event.amount` again, so a second defence component would have taken the full blow, which
      is what armour would have hit first. A breach was reported only when it scored, so breaking a
      faction-mate's shield told the attacker nothing. And `hasattr(self, 'outer_defense')` was
      always true, which closes one of the entries in
      [ADR 0019](../docs/adr/0019-machines-drive-components-through-one-vocabulary.md).

      `Event.score` is now derived from the effects, so what points were for survives beside how
      many there were. That is the material a leaderboard wants.

- [x] **The map marks what your blows did.** `PlayerPlan.effects` carries the engine's `Effect`
      under the same name, placed from what the target was doing on that tick and carrying the
      bearing it was struck from. A breached defence layer draws an arc on the face that took it,
      the machine taking damage draws a ring, and a breached hull draws the burst a wreck of your
      own already gets. Under a Hits layer, on by default.

      The bearing costs nothing: the layer that answers is always the one pointing at whoever hit
      it, so the arc needs no knowledge of which way the target was facing, and no fog of war is
      given away that shooting at something did not already give away.

- [x] **A ship's scan range is drawn.** Two dashed rings around the selected ship: where it is
      now, and where the course being plotted puts it on tick 10. The far one follows the course
      as it is dragged, which is what makes it a planning aid rather than a record.

      The radius is `ShipPlan.scan_range`, a real distance that scales with the world; the dashes
      are an affordance and stay constant on screen. It is the neutral case: what a scanner
      actually reaches depends on how visible the thing is
      ([GDDR 0031](../docs/gddr/0031-loud-things-are-seen-from-further-away.md)).

- [ ] **A gravscan cone is drawn at a made-up size.** `coneRadius` returns 7 to 21 screen pixels,
      so the wedge on the map says nothing about how far the pulse really reaches: 1200 at 30
      degrees down to 346 at 360. Two things block it.

      The reach cannot be sent as a formula, and it does not need to be: the setting is a
      `NumberInRangeParameter` over a finite range, so the engine can send the reach for every
      value it offers and the browser looks it up. That also takes the granularity back off the
      browser, which invents its own step of 5 in `coneWidthAt` today.

      What it wants first is a home on the component interface. "How far does an order to you
      reach at each setting it can take" is a question every component could answer, with a
      neutral empty for the ones whose reach does not move, but a `Gravscan` is a `Weapon` that
      is not really a weapon and the question deserves better placement than being bolted to
      `WeaponInfo`. Parked until that is thought through.

## Application services (`../arena/app`)

- [ ] **`_EngineAccess` is a shared-behaviour base wearing an access name.** It holds `_gd`,
      `list_games` and `_archive`, which is what the name promises, and then `settings`,
      `save_settings`, `all_ready`, `is_ready`, `set_ready`, `pulse`, `games_for_player` and
      `_roster`, which are shared game operations. `_roster` now builds a `Game` to answer, so a
      class named for reaching files constructs an engine object. Either thin the base to file
      access and put the shared operations somewhere honest, or rename it for what it is.

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

- [x] **24 ADRs written**, covering the layering, determinism, type objects, components,
      commands, file storage, the single WSGI app, laziness and statelessness, anchored paths,
      self-describing objects, snapshots, open information, fog of war, logins, Svelte, the URL as
      state, the two SVG layers, jointed-chain planning, the component vocabulary, explosions,
      scenarios, the three places a game lives, collisions and the encounter loop.
- [ ] **New ADRs as decisions come up.** Not a backlog to work through: write one when something is
      decided, especially when an alternative was rejected for a reason worth remembering.
- [x] **`../CLAUDE.md` folded back** to constraints plus commands, with per-directory files for
      `../arena/engine`, `../arena/app`, `../arena/api`, `../arena/admin_ui` and `game-ui`.
- [x] **`../readme.md` rewritten** as the front door: what the game is, how to run it, what is worth
      knowing before reading the code, and where the rest lives. Its old backlog was migrated into
      this file first, including the processing-order defect and the Boost crash.
- [x] **Mermaid diagrams**: the layers and the tick phases in `architecture.md`, the request
      switchboard and dev-versus-deployed in `deployment.md`.

## Documentation, continued

- [x] **Documentation meta-rules extracted into a skill**:
      `../.claude/skills/project-documentation`, with copyable templates. `share/ai-guardrails/`
      is the same thing packaged for someone on another agent, prose rules included.

- [x] **Close the console's engine imports.** `../arena/admin_ui` holds none: what a round is
      waiting for is `GameStanding`, the overview page reads `game_overview`, and the type lists
      are `ShipTypeInfo`. Moving the console onto `/api/admin/*` is now possible.

## Game features

Ideas from the original readme, kept because they are still wanted.

- [ ] **The registry rewrite: arcs, and what each race is for.** Two thirds of the fleet's weapons
      and 64% of its round damage sit on 360 degree arcs, and only three widths exist in the whole
      registry. Narrowing them is the largest source of variety available, and it makes `max_turn`
      decide fights: bringing a 30 degree arc to bear is 9 ticks for a Swarm and 4 for a Tiger.

      The races are settled. Reptilian ambushes with the best cloak and the hardest lasers, and
      lays no mines at all. Feline raids, fast and agile, cloaked but less so, carrying a few mines
      to place. Insectoid holds ground with broadsides and fields, because at 20 to 30 turn it
      cannot have narrow arcs. Human does attrition, owning EMP and nanocyte mines. Amphibian is
      standoff, which needs the payload airframe to vary: every missile in the game currently dies
      at 900 units.

      **A Gravscan is the only thing every hull carries.** Everything else is tweakable, weapon by
      weapon, and a race giving up a whole weapon class is how it comes to read as itself.

      Placeholder values to replace, all uniform where they should differ: every laser on reach
      60, every cloak on `half_power` 4 where Reptilian wants 3 and Feline 6, and `heat_per_shot`
      a class attribute so every laser in the game fires 8 times a round. Every guided payload is
      also the same airframe (speed 60, turn 45, seeker 150, cone 45, reach 900), which is variety
      going unused and needs no engine change.

      **This runs before the Gunner**, on the tools that exist: the registry is generic enough that
      any character is an upgrade. Laser damage and reach stay provisional until the Gunner makes
      them aimable, and a second pass follows if that moves them.
      Detail in [plans/ship-balance-plan.md](plans/ship-balance-plan.md).

- [x] **See explosions from far away.** An explosion carries a visibility of 1000 on the same scale
      an object's uses, so it is seen at ten times the observer's passive rating: 1560 to 3300
      against a board about 1000 across. Everybody sees every blast and where it was, and still has
      to scan to learn what was in it. A starbase went to 500 in the same pass, and a machine's
      visibility is now a model constant on `MachineType` rather than a fallback in a constructor.
      [GDDR 0031](../docs/gddr/0031-loud-things-are-seen-from-further-away.md).

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
      is spread at random to even the numbers. `../arena/app/scenarios`, screens at `/new_game`,
      `/registering` and `/registering/<game>`. The durable parts are
      [ADR 0021](../docs/adr/0021-scenarios-sit-in-the-services-layer.md),
      [ADR 0022](../docs/adr/0022-a-game-directory-moves-between-three-places.md) and
      [docs/data.md](../docs/data.md).
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
      accident. The table in `../arena/app/scenarios/five_faction_war.py` is where the answer lands,
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

## Admin / director UI (`../arena/admin_ui`)

- [x] **The game page keeps up by itself**, polling `/game_status/<game>` every 15 seconds for who
      has handed in and who has said ready. It costs no round load. When the round has moved on
      the whole page is stale, so it reloads.

- [ ] **Scenario builder.** The long-term goal: world objects, NPCs, story beats, timed triggers,
      pick-ups, objective missions (protect a VIP, and so on). Grow it out of the admin UI,
      reusing the map and drag components from the game UI. The new-game screen's row editor is
      the start of its data model.

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

- [ ] **Four encounter tests that should exist and do not.** A missile's last sighting agreeing
      with where its blast is; a ship bouncing and being caught in a blast in the same tick; a
      surface and a trigger at the same fraction resolving in one pass; and a wedge, where an
      object bounced off one surface into another spends the rest of the tick there.

      The last two are unreachable in play today, because five rocks of radius 40 sitting 294 apart
      cannot wedge anything. That is exactly why the rule must not depend on the layout, and why
      the test has to build its own geometry rather than use a scenario.

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
- [x] **`test_distribute_ships` is flaky.** Gone with the move of deployment into
      `arena/app/scenarios/placement.py`: its test seeds the generator, so the placement it checks
      is the same one every run.
- [ ] Game pickles are regenerable and gitignored: on schema drift, **delete them** rather than
      adding compatibility shims. Player orders live in `commands/*.txt` and are tracked, so they
      survive. The console's **Regenerate** button replays a game from its ships file and orders.
