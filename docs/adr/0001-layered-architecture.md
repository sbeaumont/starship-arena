# 0001. Layered architecture with a services seam

**Status:** Accepted

## Context

One engine is played through three interfaces: a Svelte map for players, a Flask console for the
director, a CLI for the host. They want different things from the same game.

Storage is pickle files today. SQLite is plausible later, and so is deriving history by replay
instead of storing it.

The old report generator rendered engine objects straight into Jinja templates. Changing an engine
object meant hunting through templates to see what broke, and the reports and the API drifted into
two accounts of the same round.

## Decision

`arena/app` is the seam. It exposes operations in domain terms and returns DTOs: plain dataclasses
with no framework in them.

Above the seam nobody handles an engine object, a `GameDirectory` or a file path. Each interface
has its own facade on top, speaking its own vocabulary.

The CLI may reach the engine directly. It is the tool you use from a shell on the host when the
seam itself is what's broken.

## Consequences

Storage can move without an interface noticing.

Every new operation an interface needs costs a service method and usually a DTO. That's real
friction, and it's the price of the seam meaning anything.

The console currently breaks this: `arena/admin_ui` imports the engine in 4 places, all in
`appfacade.py`. Known, on the backlog.

Closing that also makes something else possible: the console could become an HTTP client of
`/api/admin/*` and move to its own deployment, which is impossible while it reads the filesystem
in-process.

## Alternatives rejected

**Interfaces talking to the engine directly.** No ceremony, and it is what the report generator
did. Engine changes then ripple into every interface, and two interfaces answering the same
question drift apart, which is exactly what happened between the reports and the API.

**One shared facade for all interfaces.** It has to serve the console and the API both, so it ends
up as the union of two vocabularies, and neither reads well.
