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

One WSGI application on 8080, the way the host runs it: console at `/`, game at `/play/`, API at
`/api/`. No hot reload. Worth using before deploying, since it's the only way to see the merged
shape locally.

Cookies ignore ports, so signing in on 5173 also signs you in on 8080.

## Logging in

```
./arena-link.sh                                   who can log in
./arena-link.sh Serge http://localhost:5173 --director
./arena-link.sh Menno http://localhost:5173
```

The address is where the game UI is: Vite answers at its root, the merged app under `/play`. Set
`SITE_URL` in `secret.py` and you can leave it off, but that address is the one players use, so
pass a local one explicitly when testing.

Issuing again replaces the old link.

## Testing

```
uv run --group test python -m unittest discover -s test -t .
```

The `test` group provides httpx2, which FastAPI's TestClient needs.

Tests that need game data copy it into a temp directory. One that doesn't yet:
`test_run_test_games.py` runs against `./test/test-games` directly and moves the state of
`test-game`. It's on the backlog.

## Game data

`test/test-games/` holds playable games. The text files are tracked, the pickles are not, because
[they're derived](data.md).

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