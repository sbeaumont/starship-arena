# 0005. Commands are validated before they run

**Status:** Accepted

## Context

Players write orders as text, one per line, `<tick>: <command>`. In the original play-by-mail game
a mistyped order was discovered a week later, when the results came back.

An interactive UI can do better, but only if something can check an order without running the
round.

## Decision

Orders parse into `Command` objects that pull `Parameter` objects from the components they
address. Parsing and validation are one step, separate from execution.

`parse_commands` is called by both the interface, to check, and the engine, to run. Same code, so
what the UI accepts is what the round executes.

A `CommandSet` holds one ship's orders for one tick and runs them in the right order within it.

## Consequences

The game UI can say "that is not a valid firing angle" while the player is still planning.

A command that fails at execution records an `InternalEvent` on the ship, so it shows up in the
round's log rather than silently doing nothing. Every refusal is feedback a player can read.

Validation happens against a wider world than execution: an order may name something the ship has
scanned before, even if it has since been destroyed. Otherwise refusing the order would reveal the
kill. Execution then parses against live objects only, so the shot finds nothing.

Ordering within a tick lives in the `CommandSet`, not in the commands. That keeps all of it
visible in one switch, which is what makes it easy to move a command between phases while
debugging.

## Alternatives rejected

**Validating with a separate rule set.** Two implementations of "is this legal", guaranteed to
disagree eventually, and the disagreement only shows up as a round that executed something the UI
promised was fine.

**Each command declaring its own execution phase.** Tidier per class, but the tick's ordering is
then scattered across a dozen files and can only be understood by reading all of them.
