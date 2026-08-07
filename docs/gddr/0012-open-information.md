# 0012. Ship statistics are public

**Status:** Accepted

## Context

A game like this can hide what each ship model can do, so that discovering an opponent's
capabilities is part of play.

The players are friends. Rounds take a week. Nobody enjoys losing to a number they had no way to
know.

## Decision

Every ship model's statistics are public: hull, speed, turn rate, acceleration, energy, shields,
weapons and their arcs. The Ships page lists all of them to anyone, logged in or not.

What stays hidden is what's happening now: positions, courses, orders, and the state of a
particular ship.

## Consequences

The ships reference and the manual are reflection over the type registry, so they can be public
without maintenance.

The tactical game is about position, timing and reading intent, rather than about knowing a table
the other player hasn't seen.

New ship models can't surprise anyone by their numbers. They surprise by how they're flown.

Scoreboards can be open too, which is what makes the selector a standings page rather than a login
wall.

## Alternatives rejected

**Hidden statistics, discovered by scanning.** Thematic, and it turns a week-long turnaround into
guesswork against unknowns. It also means maintaining what each player has discovered, which is
real machinery for an effect nobody asked for.
