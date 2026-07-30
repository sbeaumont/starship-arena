# 0004. Components own their parameters and their status

**Status:** Accepted

## Context

Ships are built from components: shields, lasers, launchers, scanners, cloaks. Each takes
different orders, and each has different things worth reporting.

Two consumers need to know about them without knowing what they are. A player interface must offer
the right control before an order is given, and the history must record what every component was
doing on each tick.

## Decision

A component answers three things for itself:

- `expected_parameters`: what an order needs, each parameter validating its own input
- `status`: what changes about it during play, as name and value
- `specs`: what its type object says it is, through the same shape

A `Parameter` reports its `kind` (`direction`, `number_in_range`, `on_off`, `object_name` and so
on) so an interface knows which control to offer without ever seeing a Python class name.

## Consequences

The firing UI is generic. It reads `kind` and renders a slider, a target picker or a plain button,
and a new kind of weapon needs no UI change as long as its parameters are already-known kinds.

The condition panel renders whatever `status` returns, in the order the machine carries its
components. It has no idea what a shield is.

Validation lives with the component that owns the rule, so a bad order is refused with a message
before the round runs.

The split between `status` and `specs` has to be maintained by hand. A firing arc is a
specification, a temperature is a condition, and only the component knows which is which.

## Alternatives rejected

**Interfaces knowing component types.** A UI that checks `if isinstance(weapon, Launcher)` needs
changing every time a component is added, and leaks the engine's classes into the browser.

**Matching on wording.** Reading `status` and looking for the string "Ammo" works until someone
rewords it. The component names its own fields; nothing downstream pattern-matches prose.
