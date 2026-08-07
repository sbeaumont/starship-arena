# CLAUDE.md

Constraints for working in this repository. Directories have their own `CLAUDE.md` with the rules
that bind only them.

Starship Arena recreates a 1991 play-by-mail space combat game. Players command starships, a round
is 10 ticks, and one engine is played through three interfaces.

## Read these three first

Before the first answer about this codebase, not when you reach the area. 24kB together.

| | |
|---|---|
| [docs/architecture.md](docs/architecture.md) | The layers, the phases of a tick, and the ten invariants |
| [docs/information.md](docs/information.md) | The six places a fact can live, and how to pick one |
| [docs/glossary.md](docs/glossary.md) | The words. Different ones is how vocabulary drifts |

Then the decision record that governs what you are about to touch. **ADRs** are how it is built,
**GDDRs** are how it is played, and they share one run of numbers:
[docs/adr/README.md](docs/adr/README.md), [docs/gddr/README.md](docs/gddr/README.md). These are the
ones that bite:

| touching | read |
|---|---|
| a component, or anything a machine asks its parts | [ADR 0019](docs/adr/0019-machines-drive-components-through-one-vocabulary.md) |
| the tick's order, or anything timing-dependent | [ADR 0002](docs/adr/0002-deterministic-rounds.md), [ADR 0023](docs/adr/0023-a-tick-advances-by-encounters.md), and invariant 1 |
| damage, warheads, blasts | [GDDR 0020](docs/gddr/0020-explosions-do-not-take-sides.md) |
| terrain, collisions, what a bounce costs | [ADR 0023](docs/adr/0023-a-tick-advances-by-encounters.md), [GDDR 0025](docs/gddr/0025-terrain-bounces-you-and-costs-hull.md) |
| orders, validation, what a weapon asks for | [ADR 0005](docs/adr/0005-commands-validated-before-execution.md), [ADR 0004](docs/adr/0004-components-own-their-parameters.md) |
| history, snapshots, the map | [ADR 0011](docs/adr/0011-snapshots-hold-values.md), [GDDR 0013](docs/gddr/0013-fog-of-war-from-scans.md) |
| what a player is allowed to know | [GDDR 0012](docs/gddr/0012-open-information.md), [GDDR 0013](docs/gddr/0013-fog-of-war-from-scans.md) |
| races, factions, who flies what | [ADR 0021](docs/adr/0021-scenarios-sit-in-the-services-layer.md) |
| ship stats, weapons, what a hull is for | [docs/ship-balance.md](docs/ship-balance.md), and ask before rebalancing |

**Say which ones you read when proposing an engine change.** Naming none means the proposal was
reconstructed from implementation, which gets the mechanism right and the intent wrong.

The code cannot tell you why. A number that looks too strong may be compensating for something
already tried and abandoned. Ask before rebalancing anything.

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
8. A machine asks all its components the same questions, and names none of them. Composition is
   what the engine is for; a lookup by key or an `isinstance` makes the next component a special
   case. See [ADR 0019](docs/adr/0019-machines-drive-components-through-one-vocabulary.md).
9. Stale game data is regenerated, never read through a compatibility shim.
10. Round processing stays deterministic: no clock, no random numbers.

See [docs/architecture.md](docs/architecture.md).

## How to write

Prose follows [`.claude/skills/anti-ai-writing-style`](.claude/skills/anti-ai-writing-style/SKILL.md).
Comments are sparse and say *why*, never *what* and never what used to be there. A paragraph of
explanation belongs in `docs/` with a one-line pointer from the code.
See [docs/writing.md](docs/writing.md).

**Say less.** Reasoning worked out in conversation goes in `docs/` or an ADR, not into a comment.
A comment earns its place only where the code looks wrong and someone would undo it. Text on
screen says what the reader cannot already see, and nothing more.

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