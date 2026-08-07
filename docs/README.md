# Starship Arena documentation

Written for two readers: someone new to the code, and an AI agent asked to change it. Both want
the same thing: what the pieces are, and why they're that way rather than some other way.

| | |
|---|---|
| [architecture.md](architecture.md) | The layers, what lives where, how a round and a request flow |
| [glossary.md](glossary.md) | Round, tick, faction, contact, commander, director, order |
| [information.md](information.md) | The six places a fact can live, how to pick one, and every element classified |
| [data.md](data.md) | The game directory, plan files versus saved state, and every file's format |
| [orders.md](orders.md) | The order language: its grammar, who owns which part, what is checked |
| [deployment.md](deployment.md) | One WSGI application, the host's constraints, the build step |
| [development.md](development.md) | Running, testing, regenerating game data |
| [ship-balance.md](ship-balance.md) | What the hulls are worth against each other, and which mechanics decide fights |
| [writing.md](writing.md) | Prose style, and how sparse comments in code should be |
| [adr/](adr/) | How it is built: one decision per file, including what was rejected |
| [gddr/](gddr/) | How it is played: one game design decision per file, same shape |

## How these fit together

**This directory describes and decides. [`TODO.md`](../TODO.md) plans.** If something is not done
yet it belongs in the backlog. Documentation that describes intentions ages badly, because
nothing forces it to come true.

**The overview describes; the decision records argue.** `architecture.md` says what the layers are.
An ADR says why, what it costs, and what was rejected. Keeping them apart means the overview can be
rewritten freely without disturbing the reasoning.

**Two kinds of decision, two directories.** An **ADR** is about how the thing is built: layers,
storage, components, hosting, UI technology. A **GDDR** is about how the game is played: what a
player may know, what a weapon does, what an order feels like to give. Interface decisions land in
whichever one they are really about, so the SVG layering is an ADR and dragging a jointed chain is
a GDDR. They share one run of numbers, so a reference to 0020 is unambiguous.

**`CLAUDE.md` files are documentation too.** The root one holds the general constraints; each
component directory holds the rules that bind only it. Short, with a pointer into `docs/` for the
reasoning, so an agent reads what it needs where it's working.

**Every document here is current, not a trail.** When something changes, the file that describes it
changes with it, ADRs included. Git holds what it used to say. A doc describing what we used to do
gets read as what we do, which is how an agent ends up implementing a decision that was reversed.

**`plans/` is scratch.** A plan is the working document for one piece of work: the order the steps
go in and what will bite. Decisions made along the way move into an ADR or into this directory, and
the plan is deleted once the work lands.