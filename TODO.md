# TODO

Running list of what is next and what is deliberately parked. Newest thinking at the top of
each section.

## Game UI (`game-ui/`)

- [ ] **Logins.** No auth at all today: the selector shows every player and relies on honour.
      Preferred shape is a **magic link per player** (mailed with the round results) rather than
      accounts with passwords — it suits play-by-mail and needs no user management. Note the
      abandoned `arena/admin_ui/user.py` + `forms.py` are broken (they import a `config` module
      that no longer exists and keep plaintext passwords); treat auth as new work, not a revival.
- [ ] **Time-scrubbing within a round.** Round-by-round works; stepping tick by tick does not.
      The data is already per tick, so this is a UI slider over `TickState`.
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

- [ ] **Separate history from the entities.** `ObjectInSpace` is both the live object and its own
      per-tick archivist. Staged plan: (1) pull the recorder/timeline out of the entity,
      (2) if replay and scenarios become central, make the timeline *derivable* by re-running the
      deterministic step (a round is already a pure function of prior state + command files),
      (3) optionally a pure step function over immutable state. **Not** ECS. The DTO seam means
      none of this is visible to the UI.
- [ ] **Snapshot aliasing bug.** `snapshot['defense'] = self.defense.copy()` copies the *list*
      but shares the component objects, so historical component state reflects final values
      rather than per-tick values. Real bug, worth fixing whenever history is touched.
- [ ] **NPC controllers build commands from text.** `Pilot`/`Gunner` format a string and hand it
      to the parser. If they go live, construct `Command` objects directly and add
      `Command.as_text()` for reports and logs — validation lives in `Command.__init__` /
      `Parameter.is_valid`, not in the parsing, so nothing is lost.
- Decided against: making each `Command` declare its own execution phase. The switch in
  `CommandSet.add` keeps all the tick ordering visible in one place, which is what makes it easy
  to move a command between phases while debugging.

## Admin / director UI (`arena/admin_ui/`)

- [ ] **Scenario builder.** The long-term goal: world objects, NPCs, story beats, timed triggers,
      pick-ups, objective missions (protect a VIP, and so on). Grow it out of the admin UI,
      reusing the map and drag components from the game UI.
- [ ] The admin pages are still the original hand-written Flask templates; they have not been
      revisited since the rename from `arena/web`.

## Hosting

Currently deployed on PythonAnywhere as a single WSGI Flask app. `arena/serve.py` now bundles
everything into one WSGI application so that shape does not have to change: `/api/...` to the
FastAPI app through `a2wsgi`, `/play/...` to the built UI as static files, everything else to the
Flask admin pages. No Node at runtime — `npm run build --prefix game-ui` is a build step.

- [ ] **Update the PythonAnywhere WSGI file.** It still says
      `from arena.web.app import app as application`, and `arena/web` was renamed to
      `arena/admin_ui`, so the next deploy would fail on the import. It should become
      `from arena.serve import application`.
- [ ] **Set `GAME_UI_URL=/play`** in the host's environment so the admin pages link to the
      bundled UI rather than the Vite dev server.
- [ ] **Deploy needs the build committed or built on the host.** `game-ui/dist` is currently
      untracked; either commit it or run the build as part of deploying.
- [ ] **Consider dropping the CORS entry** in `arena/api/app.py` when serving from one origin —
      it exists only for the Vite dev server on :5173, and is harmless but no longer needed.
- [ ] Longer term, if the admin pages should stay off the public internet, they can move to a
      separate deployment — but they would then need converting into a client of `/api/admin/*`,
      since today they call the services layer **in-process** and read game data from the
      filesystem.

## Testing / data

- [ ] There is no test covering the game API beyond command validation
      (`test/api/test_fastapimain.py`). The planning endpoint and the overview are only checked
      by hand.
- [ ] Game pickles are regenerable and gitignored: on schema drift, **delete them** rather than
      adding compatibility shims (see `arena/engine/objects/machineinspace.py` history). Player
      orders live in `commands/*.txt` and are tracked, so they survive.
