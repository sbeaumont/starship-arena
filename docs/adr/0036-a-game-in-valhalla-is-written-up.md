# 0036. A game in Valhalla is written up

**Status:** Accepted

## Context

A game that is over arrives in Valhalla as a standing and a replay: some factions, some numbers,
and every tick of it to scrub through. Why round 4 went the way it did is in nobody's file. It is
in the head of the commander who guessed wrong, and that is the half of a game worth reading.

The list has the same gap one level up. It opens on scores, and nothing on it says which of these
was a six-week grind and which ended in a rout in the second round.

So a game that is over takes writing, from the director who ran it and from the commanders who
flew in it.

## Decision

Three things sit in a game's Valhalla directory beside `replay.json`:

    synopsis.txt     the director's account of the game
    win-story.json   how the side that took it says it was taken
    stories.jsonl    one line per commander: their name, and their own account

Neither is in the exported document. That document is what the engine played, validated against a
frozen schema at both doors, and exporting again overwrites it whole
([ADR 0034](0034-a-finished-game-is-exported-to-a-schema-of-its-own.md)). Overwriting is how a game
already in Valhalla picks up a schema that has grown since it went in, and anything written by a
person inside that file would go under the next export, or would force the writer to read the old
file back before it could write the new one.

Who writes what:

- The **synopsis** is the director's, written in the console. One per game.
- The **win story** belongs to the side that came first, and any commander who flew for it may
  write over what another wrote. One per game, shared, and the name on it is whoever wrote it
  last. Which side that is comes off the standing, best first, so nothing stores a winner.
- A **story** is one commander's, written on the Valhalla page in the game UI. Theirs alone: the
  name comes from the login cookie, and the game's own file says who flew there.

Saving empty text takes any of the three down again.

Reading stays open, because a game that is over is
([GDDR 0035](../gddr/0035-a-finished-game-is-watched-from-any-side.md)), and what people wrote
about it is public with it. Writing takes a login, since a story is signed.

Both are markdown of the small kind: headings, bold, italic, lists, paragraphs.
`game-ui/src/lib/markdown.js` is the whole renderer, and it escapes the text before any rule runs,
so markup somebody types is markup a reader sees. Links are not in the subset, which is what keeps
a page anybody with a login can post to from being worth posting to.

The export also copies the game's `ships.jsonl` in, so the directory says who flew what without
anybody parsing two megabytes of document to find out.

## Consequences

A story has no deadline. There is no round to be over, so a commander can come back years later
and change what they said, and nothing anywhere is stamped with when they said it.

A game nobody has written up reads exactly as it did before, since both files are absent until
somebody writes one. The museum is not waiting for them.

Nothing validates prose. A name typed into `stories.jsonl` by hand is a name, and the director can
fix one with an editor.

## Alternatives rejected

**A field in the schema, as version 2.** One file holds everything about a game, which is the
whole promise of the format. It also puts prose that changes on a Tuesday inside the one document
meant to be frozen: every edit becomes a load, a validate and a rewrite of two megabytes, and the
writer has to carry the old file's prose across or lose it.

**One file per story, named after the commander.** Simple to read and simple to edit. It also
builds a path out of a name a person typed, and player names come from a registration form.

**A story on the player rather than on the game.** That is a profile page. People want to read
about the game, and the ships they were shooting at are in the entry for it.

**Markdown through `marked` and a sanitiser.** Correct in every corner the hand-rolled subset gets
wrong, at the cost of the first two runtime dependencies the game UI has ever had, to support a
syntax beyond what anybody asked for.