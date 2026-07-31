# Starship Arena documentation

Written for two readers: someone new to the code, and an AI agent asked to change it. Both want
the same thing: what the pieces are, and why they're that way rather than some other way.

| | |
|---|---|
| [architecture.md](architecture.md) | The layers, what lives where, how a round and a request flow |
| [glossary.md](glossary.md) | Round, tick, faction, contact, commander, director, order |
| [information.md](information.md) | The six places a fact can live, how to pick one, and every element classified |
| [data.md](data.md) | The game directory, plan files versus saved state, and every file's format |
| [deployment.md](deployment.md) | One WSGI application, the host's constraints, the build step |
| [development.md](development.md) | Running, testing, regenerating game data |
| [writing.md](writing.md) | Prose style, and how sparse comments in code should be |
| [adr/](adr/) | One architecture decision per file, including what was rejected |

## How these fit together

**This directory describes and decides. [`TODO.md`](../TODO.md) plans.** If something is not done
yet it belongs in the backlog. Documentation that describes intentions ages badly, because
nothing forces it to come true.

**The overview describes; the ADRs argue.** `architecture.md` says what the layers are. An ADR
says why, what it costs, and what was rejected. Keeping them apart means the overview can be
rewritten freely while the reasoning stays put.

**`CLAUDE.md` files are documentation too.** The root one holds the general constraints; each
component directory holds the rules that bind only it. Short, with a pointer into `docs/` for the
reasoning, so an agent reads what it needs where it's working.

**An ADR is never edited once accepted.** A decision that changes gets a new ADR that supersedes
the old one, and the old one stays readable. The point is the trail, not the tidiness.