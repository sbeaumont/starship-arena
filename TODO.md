# TODO

Running list of what is next and what is deliberately parked. Newest thinking at the top of
each section.

## Next, in order

1. **Documentation** — `docs/` with an architecture overview and ADRs.
2. **Player management** — archiving, deactivating, the leaderboard.
3. **Large objects** — solid bodies and crossing them (see Engine).
4. **Scenario builder.**

## Game UI (`game-ui/`)

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
      `Command.as_text()` for reports and logs — validation lives in `Command.__init__` /
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

- [ ] **First pass** - the ones where drift would actually hurt: layered architecture and the
      services seam; DTOs at the seam; pickle storage and the no-compatibility-shims rule; one
      WSGI application; nothing with a thread or event loop at import; paths anchored to the
      repository; objects describing themselves through abstract properties rather than class
      attributes or MRO inspection; snapshots holding values and not references; open information
      as a design principle; magic-link logins with the name as identity.
- [ ] **Then, as each area is touched**: Type Object for machine types; the component registry by
      reflection; commands and `Parameter.kind`; a round as a pure function of prior state and
      command files; refused commands as player feedback; faction-shared fog of war and derived
      courses; validating orders against everything you could know; Svelte 5 without SvelteKit;
      the view living in the URL; the two SVG layers; forward-kinematics course planning;
      world-fixed north-up; registration limited to unused names; the console being director-only.
- [ ] **Fold `CLAUDE.md` back to a pointer** at `docs/` plus the genuinely agent-specific rules.
      It currently carries architecture description that will contradict `architecture.md` the
      first time either changes.
- [ ] **Decide what `readme.md` becomes** - a short front door into `docs/`, most likely.
- [ ] Diagrams as Mermaid in Markdown: renders on GitHub, diffable, top-down with the UI on top.

## Player management

The lists grow without bound as games pile up, so this is about keeping them maintainable.

- [ ] **Archive a game.** An archived game is no longer referenced anywhere: not in the console's
      list, not in a player's games, not in the roster that decides whether a name is claimable.
      Its data stays. Needs a decision on where the flag lives - a marker file in the game
      directory, or an archived subdirectory.
- [ ] **Unarchive**, and **delete an archived game for good** - deletion only from archived, so it
      is always two deliberate steps.
- [ ] **Deactivate a player.** The name stays reserved (nobody else can claim it, and old games
      keep naming them), but they cannot log in and are not offered when setting up a new game.
      Distinct from revoking a link, which only takes away the current token.
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

- [ ] **Scenario builder.** The long-term goal: world objects, NPCs, story beats, timed triggers,
      pick-ups, objective missions (protect a VIP, and so on). Grow it out of the admin UI,
      reusing the map and drag components from the game UI. The new-game screen's row editor is
      the start of its data model.

## Hosting

Deployed on PythonAnywhere as a single WSGI app: `arena/serve.py` sends `/api/...` to the FastAPI
app through `a2wsgi`, `/play/...` to the built UI as static files, and everything else to the
Flask console. No Node at runtime — `npm run build --prefix game-ui` is a build step. Deploying is
`git pull` and a reload; every default in `arena/cfg.py` is the deployed one and all paths are
anchored to the repository rather than the working directory.

**The host preforks with Python threads disabled.** uWSGI loads the app in a master process and
forks the workers, and a fork keeps only the calling thread — so anything with a background
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
- [ ] **Rebuild and commit `game-ui/dist` whenever the UI changes** — it is tracked, because the
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
      deployment — but it would then need converting into a client of `/api/admin/*`, since today
      it calls the services layer **in-process** and reads game data from the filesystem.

## Testing / data

- [ ] **The test suite writes into the committed test data.** `test_run_test_games.py` uses a
      cwd-relative `'./test/test-games'` and re-runs `setup_game()` on the real `test-game`, so
      running tests changes which round it is on. Should work on a copy.
- [ ] There is no test covering the game API beyond command validation
      (`test/api/test_fastapimain.py`). The planning endpoint and the overview are only checked
      by hand.
- [ ] Game pickles are regenerable and gitignored: on schema drift, **delete them** rather than
      adding compatibility shims. Player orders live in `commands/*.txt` and are tracked, so they
      survive. The console's **Regenerate** button replays a game from its ships file and orders.
