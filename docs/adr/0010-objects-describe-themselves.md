# 0010. Objects describe themselves through abstract properties

**Status:** Accepted

## Context

Interfaces need to know what an object is without knowing the engine's classes. A map needs to draw
a ship differently from a missile. A log needs to colour a hit differently from an energy reading.
A planner needs to know which control a weapon input wants.

Three ways to get that: a class attribute on each subclass, inspecting the class hierarchy at
runtime, or asking the object.

## Decision

The object answers, through a property each subclass implements:

- `type_name`: the model, `A2527`
- `category_name`: the family, `Ship`, `Starbase`, `Missile`, `Mine`
- `Event.kind`: `internal`, `hit`, `explosion`, `scan`
- `Parameter.kind`: `direction`, `number_in_range`, `on_off`, `object_name`, and so on

Abstract on the base, so a new subclass cannot forget.

## Consequences

Interfaces key off these and never hold a list of names. The map decides blip shape from
`category_name`, the log colours from `kind`, the firing panel picks a control from
`Parameter.kind`. A new ship type or event needs no interface change.

Nothing downstream pattern-matches prose. Reading a status string and looking for the word "Ammo"
works until someone rewords it.

Each new subclass implements a handful of small properties. That's the cost, and it's paid once
per class.

## Alternatives rejected

**A class attribute, `category = 'Ship'`.** Rejected by the author. It's data hanging off a class
rather than something the class answers, and nothing forces a subclass to set it.

**Inspecting the MRO.** Deriving the family by walking base classes. Clever, invisible, and it
couples every reader to the shape of the hierarchy, so a refactor that inserts a base class changes
what things report.
