# 0006. Game data is files, and the derived part is disposable

**Status:** Accepted

## Context

A game is a roster, orders, and the state at the end of each round. It's a hobby game with a
handful of players and a few dozen games.

Rounds are already [deterministic](0002-deterministic-rounds.md), so end-of-round state can always
be rebuilt from the roster and the orders.

## Decision

Everything lives in files under one data root. A directory per game holding `ships.jsonl`, a
`commands/` directory, and a pickle per round. One `players.jsonl` at the root.

The text files are the game and are tracked. The pickles are derived and are gitignored.

A list is **JSON Lines**: one object per line, no header, the keys naming the fields. Command
files stay plain text, because `3: Fire R1 90` is what a player types.

## Consequences

There's no database to run, migrate or back up. Copying a game is `cp -r`.

Hand-editing works, and it's the escape hatch when something is wrong: adding a line to
`players.jsonl` is how you let yourself back in when locked out.

A line per record still diffs one line per ship and is still hand-editable, and an absent key is
how a fact says it does not apply: no player, no faction, no coordinates yet.

No value may contain a space, because a game name becomes a directory and a ship name is part of a
command file's name. Names get underscores instead.

Reading a game costs unpickling. That's fine at this size, and would not be at ten times it.
Moving to SQLite means changing one layer, because [nothing above the seam knows where data
lives](0001-layered-architecture.md).

## Alternatives rejected

**A database from the start.** More to run and back up, and it buys nothing until concurrent
writers or real query load appear. Neither is close.

**Whitespace columns with a header line**, which is what these files were until the respawn work.
It reads beautifully for data that is naturally a table, and it cannot express an absent field: a
row with no token collapses into the gap and the role is read as the token, and there is no way to
write "this ship has no player". Both of those were real bugs. YAML would fix that and costs
indentation for something that is a list of flat records.
