# 0002. Rounds are deterministic

**Status:** Accepted

## Context

Game state is saved as pickles at the end of each round. Pickles go stale whenever the objects
inside them change shape, and this codebase changes shape often.

A stale pickle leaves two options: migrate it, or throw it away and rebuild. Rebuilding is only
possible if replaying the same inputs gives the same game.

## Decision

A round is a pure function of the previous round's saved state plus the command files. Same
inputs, same game, every time.

Nothing in round processing reads a clock or draws a random number.

Setup does draw, to spread factions around the origin, and then writes the resulting coordinates
back into `ships.jsonl`. So even the placement replays.

## Consequences

Stale saved state is deleted and rebuilt from the text files, which is why there are no
compatibility shims anywhere.

The console's Regenerate button exists because of this, and so does the ability to change what a
snapshot holds without stopping to think about old data.

Any future feature wanting randomness needs a seed stored with the game, and that seed becomes
part of the round's inputs.

Replaying a game against newer engine code gives different combat outcomes. Same orders, moved
rules. That is not a bug, but it does mean a replay is not a way to verify old results.

## Alternatives rejected

**Migrating saved state.** Every schema change grows a shim, the shims accumulate, and the code
ends up describing shapes that no longer exist anywhere. For a game whose data is regenerable in
under a second, that is a lot of machinery to avoid deleting a file.

**Randomness in combat.** Tempting for realism, and it would make replay impossible, which costs
more than it gives.
