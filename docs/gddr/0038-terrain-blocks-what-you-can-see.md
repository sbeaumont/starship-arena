# 0038. Terrain blocks what you can see

**Status:** Accepted

## Context

A scan was a distance: in range and you saw it, out of range and you did not. An asteroid was a
thing to steer around and nothing else, so a field of them changed where you could fly and never
what you knew. Two ships either side of a rock the size of a town watched each other through it.

That makes terrain scenery. A map is laid out to give the fight a shape, and it could only ever
shape the flying.

## Decision

**A body between the looker and what it is looking at blocks the scan.** Blocked or not, with no
falloff for a graze: a partial answer is a number nobody can picture while they are planning a
course.

`World.blocks_sight` answers it, and `can_scan` asks after the range check, which is the cheaper
question and throws most pairs out first.

**A laser is blocked too.** `Laser.can_fire_at` already goes through `can_scan`, so it costs
nothing and it stops the thing that would read as a bug: a shot through a rock you cannot see
through.

**An explosion is not blocked.** Seeing that something went off, and where, is what keeps an early
round from being an empty map, and that is worth more than the consistency
([0031](0031-loud-things-are-seen-from-further-away.md)). You still have to scan the wreck to learn
whose it was.

**Terrain itself is always known, and is never scanned.** It is chart rather than contact: in
every side's picture whole, and no ship spends a sweep finding one. `is_terrain` is what answers,
because not moving is a different fact: a starbase cannot move either and has to be found, and so
will anything else that sits still and is worth hunting for.

## Consequences

A rock is cover. Breaking line of sight is a move, an asteroid field is somewhere to lose a
pursuer, and a cloak is no longer the only way to be somewhere unseen.

Contacts go stale in a way they did not. A track that stops because the target went behind
something reads exactly like one that stops because it left range, and a player has to work out
which. That is the game.

**Every scenario inherits this.** The five-faction ring now hides ships from each other on the far
side of a rock, which was not true when it was laid out. Terrain count and terrain size are now
levers on how much anybody knows.

**Nobody scans a rock any more**, so the picture the services layer builds puts terrain in from the
world rather than from scan events, in the plan, in the replay and in a game read back out of
Valhalla. A file written before this reads under today's rule: what is on the chart is a rule of
the game, not something the file records.

## Alternatives rejected

**A graze that degrades rather than blocks.** Physically nicer, and it asks a player to picture a
percentage while dragging a course. A rule you can see on the map beats a curve you cannot.

**Blocking explosions as well.** Consistent, and it takes away the one thing that tells a player
the game is happening somewhere. Two rounds of an empty map is what
[0031](0031-loud-things-are-seen-from-further-away.md) exists to prevent, and terrain would have
quietly put it back.

**Terrain discovered by scanning, at a high visibility.** What it did before, and it very nearly
works: a rock at 300 is picked up long before it matters. It costs a scan event per rock per ship
per tick, which is most of a round's history in a field of eighty, and it says a chart is something
you find rather than something you are given.

**Remembering terrain once scanned.** A middle road, and it needs a memory per faction of things
seen, which is a second kind of fog on top of the one the game has. Nobody gets lost because a
rock left their screen.