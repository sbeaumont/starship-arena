# Logs, the journal, and what time it is

Scratch. Working notes for the five things game management is missing: a real log directory, a
per-game record of processing that the console can show, a Processing screen, a server timezone,
and processing hours on the player's game list.

Decisions worth keeping go into `../../docs`. The last section says which file gets what.

## The constraint that shapes all of it

Invariant 10: round processing is deterministic, no clock, no random numbers. A journal is nothing
but timestamps, so the engine cannot be the thing that writes them.

That settles the layering before any code is written. **Real time enters at the services layer.**
`../../arena/app` decided to process, so `../../arena/app` stamps the entry. `GameDirectory` appends the line
it is handed, because file layout is the engine's business and a clock is not.

Every path that processes a round already sits in `../../arena/app`, which makes this cheap:

| path | where |
|---|---|
| director presses the button | `AdminService.process_turn`, `force_process_turn` |
| last player says ready | `GameService.set_ready` (`arena/app/services.py:139`) |
| cron | `AdminService.process_due` |
| director replays | `AdminService.regenerate_game` |

Four callers, one seam, no engine change beyond two file methods.

## What exists to build on

`settings.jsonl` and `GameSettings` already carry `process_hours` and `process_on_all_ready`, and
the console already edits them per game with 24 checkboxes (`game-overview.html:146`). The
Processing screen is a second view onto machinery that works.

`process_due` already catches per game and keeps going, so one broken game does not eat the hour.
It has a return value nobody stores; that return value is most of a journal entry.

`GameDirectory.read_settings` / `write_settings` are the pattern a journal file follows, and
`GamePulse` is the pattern a Processing row follows.

`/api/game/games` is public on purpose (`../../arena/api/CLAUDE.md` rule 4), and processing hours are a
deadline rather than a tactic, so they can ride along with no new access rule. GDDR 0012 covers
this.

## Three things to settle first

### 1. The web application gets no log file

Two uWSGI workers, preforked (ADR 0008). Point both at one `RotatingFileHandler` and they will
both try to rename the file at rollover. One wins, the other keeps writing to an unlinked inode,
and records vanish in a way that looks like a heisenbug.

So: **the cron path owns a rotating file, the web application logs to stderr.** Cron is a single
short-lived process, which is exactly what `RotatingFileHandler` is safe for. PythonAnywhere
already captures and rotates each worker's stderr into its own server log, so the web half is
covered by the host and needs nothing.

Rejected: one shared file with a lock, and a file per pid. The lock is a distributed write problem
for a hobby game, and per-pid files mean grepping four places to answer one question.

This is the honest reading of "a real log directory with rotating logs". Ops output lands in
`../../logs`, and the thing that actually needed a file gets one.

### 2. The server keeps one timezone, and shifting is a UI concern

The server has a timezone, the host's, and is consistent in it. Everything stored, every hour in
`settings.jsonl`, every timestamp in a journal, every comparison `process_due` makes: one zone.
Below the API there is exactly one answer to what time it is.

Shifting to a reader's clock happens in the interface and nowhere else. It is presentation, the way
`for_display` turning underscores into spaces is presentation, and it never travels back down.

That line is what protects the setting. `process_hours` is a cron-shaped fact: cron fires on the
hour and the setting has to mean what the crontab means. Convert a director's local hour on the way
in and store the result, and twice a year daylight saving moves every deadline by an hour without
anybody touching anything.

The zone is the host's, with no setting to override it. One clock means the cron entry, the log
timestamps and the game never disagree about what hour it is. PythonAnywhere runs UTC, so hour 20
is 20:00 UTC and every screen showing an hour says which clock it is.
[ADR 0027](../../docs/adr/0027-the-server-keeps-one-timezone.md).

### 3. Journal, not log

`log` is taken twice already: the ops log, and the ship event log the player reads on the map. A
third meaning is how vocabulary drifts.

The per-game file is the **journal**. `journal.jsonl`, one JSON object per line, in the game
directory.

## The journal entry

```jsonl
{"at": "2026-08-08T12:00:02+02:00", "event": "processed", "round": 1, "by": "cron", "silent": ["Dewey"]}
{"at": "2026-08-08T13:00:01+02:00", "event": "failed", "round": 2, "by": "cron", "error": "..."}
{"at": "2026-08-08T14:12:40+02:00", "event": "processed", "round": 2, "by": "director"}
{"at": "2026-08-09T09:03:11+02:00", "event": "regenerated", "round": 5, "by": "director"}
```

`at` is ISO 8601 with the offset, in the server zone: sortable, readable, unambiguous about which
noon it means. `event` is the entry's self-description, the same idea as `Event.kind`. `by` is what
the director actually wants to know when a round appeared overnight.

**The rest of the object is a reported dict.** The console renders `at`, the event, and then
whatever other keys the line carries, as name and value. A new event kind, or a new detail on an
old one, needs no template edit. Same trick components already play with `status`
(`../../docs/information.md`, kind 6).

Plan or state? Neither, and `../../docs/data.md` currently says every file is one of the two. The journal
cannot be rebuilt by replaying, so it is not state. Nothing replays from it and losing it loses no
game, so it is not a plan. It is a third thing: a **record** of what the server did. That
distinction has to go in `data.md` or the next person will delete it during a regenerate.

No rotation. One line per round per game, a few hundred lines over a game's life.

## Steps

### Step 1: fix the ops logging - done

274 tests pass. What changed:

- `LOG_DIR`, `LOG_FILE_NAME`, `LOG_LEVEL`, `LOG_FILE_LEVEL`, `LOG_FILE_BYTES` and `LOG_FILE_KEEP`
  in `cfg.py`, env first then `../../secret.py`, anchored to `REPO_ROOT`. `../../logs` is gitignored.
  `LOG_FILE_NAME = "./logfile.txt"` was relative to the working directory, which broke invariant 5.
- `log.py` rewritten. Console at INFO, rotating file at DEBUG, 1 MB and 10 kept, and the format
  grew a timestamp. `configure_logger` takes a filename instead of a boolean and clears its
  handlers first, so calling it twice configures rather than doubles.
  `deactivate_logger_blocklist` kept for the three tests that call it, without the mutable default
  it was appending to on every call.
- Dropped `logging.basicConfig(stream=sys.stdout, level=DEBUG)` from `cli/main.py`. It was adding a
  second handler on top of `configure_logger`, so every line was printed twice.
- `round.py` logged the same tick twice, DEBUG at line 65 and INFO six lines later. Dropped the
  INFO. A round now prints one line to the console and keeps its ticks in the file.
- One log holds every game, so `process_due` names the game before its ticks run.
- The crontab line lost its redirect. PythonAnywhere captures a task's output already, and
  everything after logging is configured is in `../../logs/arena.log` anyway.

`locale.setlocale(LC_ALL, 'nl_NL.UTF-8')` is gone from `log.py`, where it was an import-time
landmine on any host without that locale. It was reached only when something had imported the
logging module, so the manual's date was Dutch from the CLI and English from the console. It is
English both ways now.

### Step 2: server timezone - done

274 tests pass. [ADR 0027](../../docs/adr/0027-the-server-keeps-one-timezone.md) holds the decision
and what was rejected on the way to it.

`../../arena/app/clock.py` is the only place that reads real time, and it reads the host's zone with no
setting in front of it. `AdminService.process_due` lost its `hour` parameter and asks
`server_now()` itself. Nothing on the host needs configuring.

### Step 3: the journal - done

[ADR 0026](../../docs/adr/0026-a-game-keeps-a-journal.md) holds the decision.
`GameDirectory.append_journal` / `read_journal`, a `JournalEntry` DTO, and `_append_journal` /
`journal` on `_EngineAccess` so both services reach it. All five processing paths write an entry,
including the failure path in `process_due`.

`By` and `ProcessingTrigger` are `StrEnum`s in `dto.py`, so they land in the JSON as plain strings.

The console's Process and Regenerate now go through `AdminService`, which they had been reaching
past the seam to do. Two of `appfacade.py`'s four engine imports are gone.

274 tests pass. Verified: two cron runs in the same hour process once and then say so, and the
entry for a forced round names the ships that were silent.

### Step 4: the game screen shows its journal - done

274 tests pass. A `details.settings` panel on `game-overview.html` like the Processing one above
it, last 20 entries, newest first, with the most recent in the summary so it reads collapsed.

`JournalLine` in `appfacade.py` is the console's own shape: the timestamp formatted, the underscores
out of the detail keys. The template loops the pairs and knows none of their names, and `event` is
the row's CSS class, so `failed` is red without anything holding a list of event kinds.

### Step 5: the Processing screen, and tabs on the game screen - done

274 tests pass.

**The game screen is three tabs**, because the journal panel had made it long. Overview holds the
factions and the graveyard, Processing holds the buttons, the settings and the journal, Edit holds
the spawn form. Nothing is collapsed inside a tab any more.

The tab lives in `location.hash`, so a reload keeps it and every redirect after a POST lands back
where the button was: `_anchor='processing'` for the four processing actions, `_anchor='edit'` for
a spawn. Panes are hidden rather than absent, so the 15-second poll still finds the order cells on
the Overview tab while you are looking at Processing.

**`/processing` is every game's clock in one place.** A row per game with its 24 hour toggles, the
on-ready flag, and when it last ran; the combined journal underneath, newest first across all
games. `save_settings` carries a hidden `from` so a save there comes back there.

Reading "settings for all games" as one screen showing every game's, each edited on its own row. A
bulk apply, tick 12 hours and push it to six games at once, is a different feature and can wait
until somebody wants it.

No polling on it. `/game_status/<game>` is there if a live view earns its place later.

### Step 6: the player's game list - done

274 tests pass, `dist` rebuilt.

`GameSummary` gained `process_hours` and `next_processing`, the next moment it runs as a full ISO
timestamp with the offset in it, `None` for a game the director runs by hand. `clock.next_occurrence`
does the arithmetic in Python, so the browser converts a moment rather than a schedule. `GET
/api/game/time` is open, like the hours themselves, and answers `{"now": ..., "zone": "CEST"}`.

`Selector.svelte` shows `server time 16:22 CEST` in the header and, per game,
`next round Sun 12:00 · in 19h` in the reader's own clock. It takes the browser's skew off the
server's answer, so a laptop with a wrong clock cannot make a countdown lie.

The one thing the browser cannot do for free: the server's zone has no name here, only an offset,
so the header's clock shifts the epoch by that offset and reads the UTC fields. Handing the string
to `toLocaleTimeString` would render the reader's clock a second time.

**Deferred: the player profile.** Storing a timezone per player buys nothing while a browser is in
the room. It starts earning its place the day the server sends email on its own schedule, since
nothing will be there to ask what "tomorrow morning" means for the person receiving it. That is
also when a profile screen gets a second field to hold, and one field is a thin reason for a screen.

When it lands: `timezone` as an optional key in `players.jsonl` (only `name` is required and a line
writes only what differs from the default), sign-up sending the browser's detected zone so nobody
picks from a list of 600, a `?page=profile` screen per ADR 0016, and the declared zone winning over
the browser's when both exist. Named fields, no settings bag: email and preferences each want their
own validation, and a `dict` in a JSON line is where typos live quietly.

## What goes into the official docs

The plan is scratch. These are not.

| where | what |
|---|---|
| **ADR 0026** (new) | A game keeps a journal of its processing. Real time enters at the services layer; the engine stays clock-free. Rejected: timestamps inside the engine, and a shared rotating file across preforked workers. |
| **ADR 0027** (new) | The server keeps one timezone and is consistent in it; shifting to a reader's clock is a UI concern and never travels back down. Rejected: converting on the way in and store the result, and why daylight saving is what kills it. Also: an automatic deadline fires once per hour, a deliberate one always runs. |
| **GDDR 0028** (new) | Processing times are part of play. |
| `../../docs/data.md` | `journal.jsonl` and its shape. The third category next to plan and state, and the rule that a regenerate leaves it alone. |
| `../../docs/glossary.md` | **Journal**, and why it is not called a log. **Server time**. |
| `../../docs/architecture.md` | One line on where a clock is allowed, next to invariant 10. |
| `../../docs/deployment.md` | The `../../logs` directory, the crontab line, and that the host's clock is the game's. |
| `../../docs/development.md` | Where the logs are and what level they run at. |

Numbering: 0025 is the highest in use across both families, and they share one run, so the three
new records are 0026, 0027 and 0028.

All three are written. The two ADRs carry the mechanism: determinism, forked workers, daylight
saving, and where a timezone is allowed to be applied. GDDR 0028 carries what a deadline means to
somebody playing.

One thing it settles that the plan had wrong: 24 hours ticked is a round an *hour*, forced. It is
readiness, the separate setting, that processes whenever the orders land.

## What will bite

**Daylight saving, twice a year.** Fall back repeats an hour, which the step 3 guard covers. Spring
forward skips one, which it cannot: a game asking for 02:00 does not run on the March morning that
has no 02:00.

**Two workers, one journal file.** Appending a line under 4kB is atomic on POSIX with `O_APPEND`,
so interleaved lines are not the risk. Reading while another process appends is, mildly: a reader
can catch a partial last line. Tolerating a short read at the end costs one condition.

**`process_due` swallows the game name on failure.** It catches broadly on purpose, and once the
journal exists a failure that cannot even open the game directory has nowhere to write itself. The
ops log is the fallback, which is another reason step 1 comes first.

**Regenerate and the journal.** Regenerating drops pickles and replays. The journal is a record of
what happened in the world, so it survives, and the regenerate is itself an entry. Anyone
implementing "delete the game's derived files" needs to know this file is not one of them.