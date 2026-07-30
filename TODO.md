# TODO

Running list of what is next and what is deliberately parked. Newest thinking at the top of
each section.

## Next, in order

1. **Ships overview and lore into the game UI**, as pages off the selector.
2. **Logins.**
3. **Scenario builder.**

## Game UI (`game-ui/`)

- [ ] **Ships overview and lore as pages off the selector.** Both still live only in the
      director's console, which players will lose access to once logins land. The ships page is
      reflection over the type registry, so it stays current on its own; lore is prose.
- [ ] **Logins.** No auth at all today: the selector shows every player and relies on honour.
      Preferred shape is a **magic link per player** (mailed with the round results) rather than
      accounts with passwords — it suits play-by-mail and needs no user management. Note the
      abandoned `arena/admin_ui/user.py` + `forms.py` are broken (they import a `config` module
      that no longer exists and keep plaintext passwords); treat auth as new work, not a revival.
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
