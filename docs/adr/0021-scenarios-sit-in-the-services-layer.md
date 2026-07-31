# 0021. Scenarios sit in the services layer

**Status:** Accepted

## Context

A scenario is the thing that turns a group of people into a roster: which factions exist, which
hulls each one flies, how many ships anybody may ask for, how players are spread across sides.

None of that is the engine's business. The engine knows ships, rounds and components; the five
registry modules named after races are a filing convention and nothing reads their names. Keeping
it that way was a deliberate call: **a race is lore.** A ship type saying `race = 'Human'` would
make an invented backstory into a model constant, and the engine would then have an opinion about
who fights whom.

The first version put scenarios in `arena/admin_ui`, on the argument that the console is the
storyteller and may hold knowledge no other interface needs.

That lasted until players had to register for a game themselves. Registration arrives through
`/api/game`, and validating it needs the scenario's ship limit. `arena/api` importing
`arena/admin_ui` breaks the rule that no interface imports another
([0001](0001-layered-architecture.md)).

## Decision

Scenarios live in `arena/app/scenarios/`, one module each, listed in the package's `__init__`.

A scenario answers for itself: `key`, `name`, `blurb`, `factions`, `max_ships`, whether it
`registers`, and `deal(entries, rng)` returning ship records. Both interfaces sit on that, the
same way they sit on `AdminService`.

What stays in an interface is that interface's own business: parsing its forms, and choosing its
template.

The engine still learns nothing. The race-to-hulls table is written out by hand in the scenario,
because deciding which side may fly a hull is a decision somebody makes, not something to derive
from a module name or a type-name prefix.

## Consequences

A new scenario is one module and no changes anywhere else, and it is visible to the console and
the API at once.

`arena/app` now holds something that is neither storage nor an engine operation. That is the
honest place for it: it is domain knowledge every interface needs and the engine must not have.

The generic "type your own roster" path became a scenario too, with `registers = False`. So the
console has one entry point rather than a scenario flow beside a legacy flow.

## Alternatives rejected

**Scenarios in the console.** Tried, and it broke the same day. The console is one interface, and
the moment a player-facing surface needed the same knowledge there was no legal way to share it.
The general shape: anything two interfaces need is below the seam, however much it feels like one
interface's private vocabulary.

**`race` as a model constant on `ShipType`.** It would have made the faction table derivable, and
it puts lore in the engine, where it would then be picked up by the manual, the DTOs and anything
else that iterates a type's attributes. A scenario that wanted Humans and Felines on one side
would be fighting the data model.

**Deriving the faction from the registry module or the type-name prefix.** `H2545` starts with H
and lives in `human.py`, so the mapping looks free. It reads a filing convention as a rule, so
moving a file or adding `H2560` to the wrong module silently changes the game.
