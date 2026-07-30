# 0003. Type objects instead of a class per ship

**Status:** Accepted

## Context

The game has 20 ship and starbase models, and wants more. They differ in hull, speed, turn rate,
energy and, mostly, in which components they carry.

A class per model gives a large hierarchy of near-identical classes.

## Decision

A `MachineInSpace` holds a reference to its `MachineType`, and asks it whenever it needs to know
what it is. The relationship mirrors object to class, but at runtime.

A type is written in Python, in `arena/engine/objects/registry/`. It declares its maxima and the
set of components an instance gets.

Instances describe themselves by asking their type: `type_name` gives the model (`A2527`), and
`name` the readable version (`A2527 Alligator`).

## Consequences

A new model is one small class in the registry and nothing else. It appears in the ships
reference, in the new game dropdown and in the manual without any of them being told, because all
three read the registry.

Type objects are shared between instances, so they must stay immutable. Anything that changes
during play belongs on the instance.

The registry is loaded by reflection, so a model that isn't imported doesn't exist. `builder.py`
walks the package to force the imports.

## Alternatives rejected

**A class per ship model.** An enormous hierarchy, most of it duplication, and no way to list the
models without reflection anyway.

**Configuration files.** JSON or YAML per model, parsed at startup. It means writing a parser and
a translation layer, and expressing "this ship carries three of these launchers" in a format that
fights back. Python already is a configuration language, and the editor already checks it.
