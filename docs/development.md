# Development

`uv` manages the virtualenv and Python 3.14. The declared floor is 3.10, because that's what the
host offers.

```
uv sync
```

## Running

```
bash arena-dev.sh
```

Three servers in one terminal, each line tagged and coloured: `api` on 8000, `ui` on 5173, `admin`
on 8080. Ctrl-C stops all of them. Hot reload on both the Python and the Svelte side.

Open 5173 for the game, 8080 for the console. Vite proxies `/api` to 8000, so the browser sees one
origin.

```
npm run build --prefix game-ui
bash arena-serve.sh
```

One WSGI application on 8080, the way the host runs it: game at `/`, console at `/director/`, API
at `/api/`. No hot reload. Worth using before deploying, since it's the only way to see the merged
shape locally.

Cookies ignore ports, so signing in on 5173 also signs you in on 8080.

## On a phone

`arena-dev.sh` listens on every interface, so the game answers at this machine's own address from
anything on the same network. Issue the link with that address rather than with localhost:

```
./arena-link.sh Menno http://192.168.1.6:5173
```

A browser keeps a `Secure` cookie over https, and over localhost, and nowhere else. A plain
address on the network would drop it and every call would come back 401, so `arena-dev.sh` exports
`ARENA_INSECURE_COOKIES=1`. Nothing else sets it and the host must not: deployed, the cookie is
`Secure` as it should be.

The map picks its shell from whether the browser has fingers. `?ui=touch` and `?ui=desktop`
override that, so either can be opened on any machine.

## Logging in

```
./arena-link.sh                                   who can log in
./arena-link.sh Serge http://localhost:5173 --director
./arena-link.sh Menno http://localhost:5173
```

The address is where the game UI is, and both answer at their root: Vite on 5173, the merged app
on 8080. Set
`SITE_URL` in `secret.py` and you can leave it off, but that address is the one players use, so
pass a local one explicitly when testing.

Issuing again replaces the old link.

## Logs

The CLI writes `logs/arena.log`, rotating at 1 MB and keeping 10. The console it prints to shows
INFO, the file keeps DEBUG, so a round's ticks are there when you want them and out of the way
when you don't.

The web application writes no file. Two preforked workers would both rename one at rollover and
the loser would keep writing to an unlinked inode, so they print to stderr and the host captures
it. `arena-dev.sh` is that stderr, tagged per server.

`LOG_DIR`, `LOG_LEVEL`, `LOG_FILE_LEVEL`, `LOG_FILE_BYTES` and `LOG_FILE_KEEP` are in
`arena/cfg.py`, all overridable from the environment.

## Testing

```
uv run --group test python -m unittest discover -s test -t .
```

The `test` group provides httpx2, which FastAPI's TestClient needs.

Tests that need game data copy it into a temp directory. One that doesn't yet:
`test_run_test_games.py` runs against `./test/test-games` directly and moves the state of
`test-game`. It's on the backlog.

## Game data

Two places, and they are not the same thing. `test/test-games/` holds the suite's fixtures, and
only games a test names belong there: `test-game` and `apitest`. `game-data/` is the local data
root the servers and the console run on, holding `games/`, `archived/` and `registering/`, all of
it gitignored. Point `GAME_DATA_DIR` at it and play with whatever you like; the suite never sees
it.

In either place the text files are the plan and the pickles are derived, so only the text is
tracked. [Which is which](data.md).

To rebuild a game after changing what the engine stores, use **Regenerate** in the console, or:

```
uv run python -m arena.cli.main setup <game>
uv run python -m arena.cli.main generate <game>
```

Run the CLI as a module. `python arena/cli/main.py` puts `arena/cli` on `sys.path` instead of the
repository, and the imports fail. One action per call: `setup` first, then `generate`.

`setup` cleans the pickles and writes round 0, so it has to come before `generate` rather than
after. Calling `regenerate_game` after a `setup` replays nothing, because setup has already taken
away the rounds it would have counted.

## Before committing

Rebuild the UI if you touched `game-ui/src`, because `dist` is tracked:

```
npm run build --prefix game-ui
```

The bundle filename carries a content hash, so expect a delete and an add.