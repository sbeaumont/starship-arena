# 0001. Example: configuration lives in code, not in files

**Status:** Accepted

<!-- A worked example, so the shape is obvious. Delete it once you have real ones. -->

## Context

The project has 20 variants of one kind of object, differing mostly in which parts they carry. New
ones get added often, by the author rather than by users.

## Decision

Each variant is a small class in a registry package, loaded by reflection.

## Consequences

A new variant is one file and appears everywhere that reads the registry, without those places
being told.

Nothing can change a variant at runtime. That is fine here and would not be if users configured
them.

## Alternatives rejected

**JSON or YAML per variant.** Means writing a parser and a translation layer, and expressing "three
of these, one of those" in a format that fights back. The language is already a configuration
language, and the editor already checks it.

**A class per variant with inheritance.** A large hierarchy, most of it duplication, and no way to
list the variants without reflection anyway.
