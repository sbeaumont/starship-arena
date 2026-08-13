# 0034. A finished game is exported to a schema of its own

**Status:** Accepted

## Context

A saved world is this month's classes on disk. A game pickled before `DrawType` went is unreadable
today, and the only cure is replaying it from its orders. Delete the orders and it is gone for
good.

So a game that is over has to be written down in text, and text needs a shape that somebody keeps.

`GameReplay` is a shape that already exists, and it is the wrong one to write down. It is a DTO. It
changes when the player's map changes, which is often, for reasons that have nothing to do with a
game played three engine versions ago. A file whose meaning is defined by a dataclass in the UI's
service moves every time somebody renames a field, and nothing anywhere complains.

The file has to be the fixed point. **The code adapts to it.**

## Decision

A game is exported to one JSON file, `replay.json`, in its own directory under `valhalla/`. The file
names its version, and each version is a package in `arena/app/valhalla/`:

    v1/schema.json      what a v1 file promises. Data, not code, and frozen the day it ships
    v1/from_engine.py   how today's object model becomes one. Expected to change
    v1/__init__.py      the two doors, and the validation both of them pass through

The definition is a JSON Schema rather than a Python class. A class ends up being three things at
once, the definition, the in-memory model and the JSON layout, so editing any of them moves the
format and nothing anywhere disagrees. A schema is a thing the code can be held against.

**Every document is validated on the way out and on the way back in.** A translator that has
stopped honouring the definition fails at the export, rather than in the museum years later with
the pickles gone. That validation is the whole guarantee: without it the rules below are a promise.

Four rules carry the rest:

1. **A version, once written, is never reinterpreted.** A later engine reads an old file as it
   meant itself, or refuses it and says which version it is.
2. **One writer, for the newest version only.** When v2 arrives the v1 writer is deleted. Nothing
   ever writes an old version again, so there is one place that decides what an export contains.
3. **A reader per version, kept forever.** When the engine moves, the translators move with it, so
   an old file keeps saying what it said.
4. **What a version cannot answer is absent.** A picture the museum grows later shows nothing for
   a game exported before it, and nothing is invented to fill the gap.

The reader hands back the document. What an interface makes of it is the interface's business, and
keeping that out of here is what lets a reader go on working when the interface moves.

### What v1 writes down

More than the replay page draws today, because what a file leaves out dies with the pickles.

Per object: name, type, category, faction, owner, radius, and **the player who flew it**. Per tick
of that object: position, heading and speed where they are known, hull, battery, each component's
`status`, the score earned, **what it saw**, and the events. Per event: its kind, what it carried,
its sentence, where it happened, and **what it manifested as** in the world.

Condition and score cost one more read on a walk that is already happening.

A shape is the event's own answer, as its name and its measurements: a beam is a line between two
points, a blast is a circle. The translator writes down whatever it is handed and names no shape,
so an event that manifests as something new needs no edit here, in the schema, or in a reader.
Blasts land in a v1 file for free, which no interface has shown before.

Component status earns its place by being a reported dict, names the component chose and values it
chose ([ADR 0004](0004-components-own-their-parameters.md)). A v1 file still shows what a cloak was
doing after `Cloak` has been deleted from the code. A format that named the fields itself could
not, so the schema declares the openness instead: an object of objects whose values are string or
number. The keys are the component's business, the shape is not.

**Scans are in it**, per object per tick, as what was seen and where. A name and a position, since
how far off and in what direction it was are worked out from the scanner's own row.

They are what a side's fog is rebuilt from, so a game that is over is watched the way it was
fought rather than as a diagram where everybody knew everything
([GDDR 0035](../gddr/0035-a-finished-game-is-watched-from-any-side.md)). A file without them
could only ever answer one question, and it would be the least interesting one.

Orders and the journal stay out because they are already text and already in the directory. Pickles
are the only thing in a game that cannot survive on its own.

## Consequences

Valhalla is a root beside the other four, and the export copies into it rather than moving anything.
The game carries on being whatever it was, so a director can take a readable backup of one about to
be archived, and declaring a game over is separate work that calls this on its way past.

Deleting a finished game's pickles then loses nothing the file holds. Measured on `xke`, 4 rounds
and 112 objects: 2.0 MB of indented JSON against 2.7 MB of pickles, most of the growth being the
scans.

Two shapes now describe one picture, the schema and `GameReplay`, each with its own walk over the
histories. That is the price, and it is the point: the map can change without changing what a file
written last year means.

**Both walks end at `GameReplay`.** `GameService.game_replay` builds it off a played game's saved
worlds and `arena.app.from_valhalla` builds it off a file, so an interface above the seam is
handed one shape and never learns which shelf a game came off. The second walk carries the fog
rule with it, which is the part that could quietly drift, so `test/app/test_the_museum.py` exports
a played game and asserts the two agree side by side.

`jsonschema` is a dependency, and the host needs it installed for a director to export anything.

While a game still has its pickles it can be exported again, so a schema that grows can be applied
to anything not yet cleaned out. Once the pickles go, what the file holds is all there is.

Exporting is what makes a game public, since Valhalla is open to anybody. A game exported while it
is still being played has both sides' fog readable from any browser.

## Alternatives rejected

**The DTO as the format**, `asdict(GameReplay)` with a version key on top. One shape, no mapper,
and it was the first thing proposed. It fails at the one job the format has: `GameReplay` answers
to the player's map, so a field renamed for the UI's convenience silently changes what every file
written after it means, and the reader for v1 spends its life chasing a shape that belongs to
somebody else.

**Dataclasses as the definition**, one per level of the document, serialised with `asdict`. Built
first. They are the definition, the in-memory model and the JSON layout at once, so the format
moves whenever somebody edits Python, and the only thing standing between a renamed field and a
museum full of nulls is that nobody meant to. There was nothing to hold the code against.

**A prose schema in `docs/`.** A second copy of the field list, with nothing checking that the two
agree. The descriptions inside `schema.json` are where a field says what it means.

**The history, written out verbatim.** Events hold references to engine objects, so writing them at
all means flattening them by hand. A format that copied the object model would be the coupling this
record exists to avoid, one layer further down.

**Keeping the pickles forever.** Space is the small half of it. A pickle only reads back into the
classes that wrote it, which is the problem rather than a cost of the alternative.