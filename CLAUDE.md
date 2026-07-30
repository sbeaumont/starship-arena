# CLAUDE.md

Constraints for working in this repository. The reasoning lives in [`docs/`](docs/); read the
relevant page before changing that area. Directories have their own `CLAUDE.md` with the rules
that bind only them.

Starship Arena recreates a 1991 play-by-mail space combat game. Players command starships, a round
is 10 ticks, and one engine is played through three interfaces.

## Never break these

1. Nothing in `arena/engine` imports anything above it.
2. Nothing above `arena/app` handles an engine object or a file path.
3. No interface imports another interface. The console goes through `AdminService`; only the CLI
   may reach the engine directly.
4. Every path is anchored to the repository, never to the working directory.
5. Nothing creates a thread, event loop or pool at import time. The host preforks.
6. Snapshots hold values, never references.
7. An object says what it is through its own properties, not through class attributes or
   inspection of its class hierarchy.
8. Stale game data is regenerated, never read through a compatibility shim.
9. Round processing stays deterministic: no clock, no random numbers.

See [docs/architecture.md](docs/architecture.md).

## How to write

Prose follows [`.claude/skills/anti-ai-writing-style`](.claude/skills/anti-ai-writing-style/SKILL.md).
Comments are sparse and say *why*, never *what* and never what used to be there. A paragraph of
explanation belongs in `docs/` with a one-line pointer from the code.
See [docs/writing.md](docs/writing.md).

## Keep it simple

Hand-crafted on purpose. No defensive programming, no abstraction without a present need, no
dependency that isn't earning its place. Fail loudly rather than fall back silently.

## Commands

```bash
uv sync                                  # environment (uv manages the venv and Python 3.14)

bash arena-dev.sh                        # all three servers: api :8000, ui :5173, admin :8080
bash arena-serve.sh                      # one WSGI app, as deployed (build the UI first)
npm run build --prefix game-ui           # the UI build, committed because the host has none

uv run --group test python -m unittest discover -s test -t .

uv run python -m arena.cli.main setup <game>       # run as a module, not as a script
uv run python -m arena.cli.main generate <game>
./arena-link.sh                                    # who can log in
./arena-link.sh <name> --director                  # a login link, address from SITE_URL
```

More in [docs/development.md](docs/development.md) and [docs/deployment.md](docs/deployment.md).