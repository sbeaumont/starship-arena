# TODO

Running list of what is next and what is deliberately parked. Newest thinking at the top of
each section.

## Next, in order

1. **Player management**: archiving, deactivating, the leaderboard.
2. **Large objects**: solid bodies and crossing them (see Engine).
3. **Scenario builder.**

## Game UI (`game-ui/`)

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
- [ ] **A new manual.** The current one is generated from `manual.html` and badly out of date.
      Decide whether it stays a PDF or becomes a page in the game UI.
- [ ] **Time-scrubbing within a round.** Round-by-round works; stepping tick by tick does not.
      Snapshots now hold per-tick component state as well as position, so a slider over
      `TickState` would show shields dropping and ammo going down, not just movement.
- [ ] **Visualise a ship kill.** A destroyed ship simply stops appearing: it drops out of the
      status file and its track ends. Blast circles are drawn already, but nothing marks *this is
      where something died*. The graveyard holds destroyed player ships, and the killing blow is
      in the witnesses' histories as a `HitEvent`.
- [ ] **Spectator view.** Whole game, tick by tick, with short tails (about three ticks) instead
      of a full round's trail. Wants a player-less view keyed on the game rather than a player.
- [ ] **Boost / Activation / Replenish controls.** All three are now describable through
      `Parameter.kind` (`shield_boost`, `on_off`, no inputs), so they can follow the same
      pattern as firing: click a tick, pick the component, get the right control. Shields are
      **ship-relative** (N is the front ±45), so draw the quadrants rotated to the heading.
- [ ] **Speed/throttle drag feel.** Dragging a node sets turn *and* speed at once; the speed
      half still feels rough. Oldest outstanding UI note.
- [ ] **Mine vectors are approximate.** A mine launches at the ship's speed *less*
      `MineType.slow_down_rate` (5), but that is not exposed, so the arrow reads ~5 units long.
      Exposing it cleanly needs a home that is not a superclass (see the rejected attempt in
      `MissileType`).
- [ ] **Laser with no resolvable target** draws a 20-unit stub instead of a beam. Harmless now
      (a target is always picked from the map) but wrong if an order survives its target.
- [ ] **Per-ship standing orders** for `Pilot`/`Gunner` once those are live: a target and a
      Defensive/Offensive mode are per-ship settings, not per-tick commands, so they belong in a
      ship panel rather than on a tick.

## Engine

- [ ] **Large objects, and crossing them.** Solid bodies with a radius, and movement that notices
      them. A tick is a teleport: `move()` translates the whole speed at once, so nothing between
      the endpoints exists. The primitive needed is "does this tick's path pass within r of a
      point, and where does it first cross" - a `Vector` knows its own path, so it can answer.
      Static bodies first: everything moves in one loop, so ship-versus-ship collision would
      depend on iteration order. Open: what a hit does (stop at the surface with damage by speed,
      or worse), whether bodies are public knowledge (probably - terrain, not fog of war),
      whether they block line of sight (big, separate), and where they are placed (`bodies.txt`
      until the scenario builder owns world objects). Gravity is a different feature; park it.
- [ ] **Warheads have the same tunnelling bug.** `Warhead.can_explode` tests distance at tick
      boundaries, after everything has moved. A Splinter travels 60 a tick and triggers within 6,
      so it can pass straight through a ship. The same path primitive fixes it - worth doing as a
      separate change from bodies, so a shift in trigger behaviour is attributable.
- [ ] **Processing order must not affect the outcome, and today it can.** Weapons fire in the
      post-move phase, so a missile launched this tick may or may not already be "in space" when
      something explodes, depending on where its launcher sat in the iteration. The common symptom:
      every rocket a ship just fired blows up when that ship is hit in the same tick. Possible
      fixes: fire pre-move, or let weapons fire only after existing objects have exploded. The game
      is built on the premise that iteration order never matters, so this is a real defect rather
      than a quirk.
- [ ] **A malformed Boost command crashes.** Long-standing.
- [ ] **Damage to individual components**, rather than only hull and shields.
- [ ] **In-game spawning**, and possibly respawning after death. Probably an admin command file,
      probably tied to scenarios.
- [ ] **Objects in space that are not machines.** Black holes, asteroids, loot crates, and
      whatever a scenario needs to put in the world. `ObjectInSpace` is already the base for
      "anything in space" rather than "anything built", and `type_name` / `category_name` are
      abstract, so a new kind answers for itself and the map keys its blip off the category
      without being told. Needed by the scenario builder.
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
- Decided against: making each `Command` declare its own execution phase. The switch in
  `CommandSet.add` keeps all the tick ordering visible in one place, which is what makes it easy
  to move a command between phases while debugging.

## Documentation (`docs/`)

Written with the author, not handed over as a draft: the intent is human understanding *and*
stopping AI drift, and the reasoning is the part only a person can confirm.

    docs/README.md         what is here, and which file answers which question
    docs/architecture.md   the layers, what lives where, how a request and a round flow
    docs/glossary.md       round vs tick, faction, contact, commander, director, order
    docs/data.md           the game directory, ships.txt, commands, pickles, players.txt
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
      in `players.txt`, and `by_token` refusing them, which closes every interface at once.
- [ ] **Leaderboard.** Per player: the last ten games and a lifetime total. A game's contribution
      is **total score divided by the number of ships they had in it**, so commanding a fleet is
      not worth more than commanding one ship well.
- [ ] **Fun statistics** alongside the score: kills, shields broken, ordnance fired, distance
      travelled. The history already records the events these come from; it is a question of what
      to count and where to keep the totals so it need not be recomputed from every round.

## Making a game easily

- [ ] **Deal players into a game.** Take a group of people and spread them evenly and randomly
      across the factions, assigning ships as you go, instead of typing the whole roster.
- [ ] **A sign-up page** where people put themselves forward for the next game, so the director
      starts from a list rather than a memory.
- [ ] **Predefined factions.** Once the scenario builder exists a scenario brings its own
      factions, so dealing people in means distributing them over *those* rather than over an
      arbitrary count.
- [ ] **More than one ship.** A player may ask for, or be given, several ships - expressed at
      sign-up or set during setup. The planning UI already handles a fleet; this is about the
      dealing.

## Admin / director UI (`arena/admin_ui/`)

- [x] **The game page keeps up by itself**, polling `/game_status/<game>` every 15 seconds for who
      has handed in and who has said ready. It costs no round load. When the round has moved on
      the whole page is stale, so it reloads.

- [ ] **Scenario builder.** The long-term goal: world objects, NPCs, story beats, timed triggers,
      pick-ups, objective missions (protect a VIP, and so on). Grow it out of the admin UI,
      reusing the map and drag components from the game UI. The new-game screen's row editor is
      the start of its data model.

## Hosting

Deployed on PythonAnywhere as a single WSGI app: `arena/serve.py` sends `/api/...` to the FastAPI
app through `a2wsgi`, `/play/...` to the built UI as static files, and everything else to the
Flask console. No Node at runtime; `npm run build --prefix game-ui` is a build step. Deploying is
`git pull` and a reload; every default in `arena/cfg.py` is the deployed one and all paths are
anchored to the repository rather than the working directory.

**The host preforks with Python threads disabled.** uWSGI loads the app in a master process and
forks the workers, and a fork keeps only the calling thread, so anything with a background
thread, event loop or connection pool must be built on first use inside the worker, never at
import. `arena/serve.py` builds the ASGI adapter that way; the symptom of getting it wrong is
every route timing out at `504-loadbalancer`.

- [ ] **Deploying the logins is order-sensitive.** The console refuses everyone until a director
      exists, so: `git pull`, then `./arena-link.sh <you> https://your.site/play --director` in a Bash
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

- [ ] **The test suite writes into the committed test data.** `test_run_test_games.py` uses a
      cwd-relative `'./test/test-games'` and re-runs `setup_game()` on the real `test-game`, so
      running tests changes which round it is on. Should work on a copy.

      The same data root is what the console runs on, so archiving a game there takes it away from
      the suite: `test/api/test_fastapimain.py` copies its fixture out of `test-games/apitest`,
      and with that game archived three tests error on a missing directory.
- [ ] **`test_distribute_ships` is flaky.** It asserts no placed ship has an x or y of exactly
      zero, but `centers_for` places them at a random angle, which occasionally rounds to it.
      Seen twice; 20 runs since have been clean.
- [ ] There is no test covering the game API beyond command validation
      (`test/api/test_fastapimain.py`). The planning endpoint and the overview are only checked
      by hand.
- [ ] Game pickles are regenerable and gitignored: on schema drift, **delete them** rather than
      adding compatibility shims. Player orders live in `commands/*.txt` and are tracked, so they
      survive. The console's **Regenerate** button replays a game from its ships file and orders.
