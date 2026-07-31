# 0006. Game data is files, and the derived part is disposable

**Status:** Accepted

## Context

A game is a roster, orders, and the state at the end of each round. It's a hobby game with a
handful of players and a few dozen games.

Rounds are already [deterministic](0002-deterministic-rounds.md), so end-of-round state can always
be rebuilt from the roster and the orders.

## Decision

Everything lives in files under one data root. A directory per game holding `ships.jsonl`, a
`commands/` directory, and a pickle per round. One `players.txt` at the root.

The text files are the game and are tracked. The pickles are derived and are gitignored.

Text files are whitespace separated with a header line naming the columns, which makes them
readable and editable by hand.

## Consequences

There's no database to run, migrate or back up. Copying a game is `cp -r`.

Hand-editing works, and it's the escape hatch when something is wrong: adding a line to
`players.txt` is how you let yourself back in when locked out.

Whitespace separation means no value can contain a space. Names get underscores instead.

Reading a game costs unpickling. That's fine at this size, and would not be at ten times it.
Moving to SQLite means changing one layer, because [nothing above the seam knows where data
lives](0001-layered-architecture.md).

## Alternatives rejected

**A database from the start.** More to run and back up, and it buys nothing until concurrent
writers or real query load appear. Neither is close.

**JSON or YAML for the text files.** Quoting and indentation for data that's naturally a table.
The current format is readable in a terminal and diffs one line per ship.
