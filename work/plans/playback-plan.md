# Stepping through a game, tick by tick

The map shows one moment: where everything was when a round ended. A playhead over every tick the
game has played is what makes it something to tell a story from, and the cheapest way to see what
actually happened in a fight.

What it has to do: step back and forward over every tick played, draw a short tail of two or three
ticks rather than a whole round of trail, rewind to the start of a round or of the game, run forward
to the end of a round or to the latest tick, play by itself, and show every faction rather than one
for the director and once a game is over.

## Done

**`Replay`** (`arena/engine/replay.py`) loads every round's saved world, keyed by round number.
The world that knows about a tick is the one saved for that tick's round, and being in space at a
tick is having a snapshot for it. That one rule handles arrivals, wrecks and spent ordnance without
a special case anywhere. Loading xke's five rounds costs 0.03s.

**The world keeps this round's dead.** Ordnance that went off was removed from the world outright,
so a missile that died mid-round was gone from the record as if it had never been fired: 94 of
xke's 112 objects, and half the salvo evaporating at every round boundary. `World.destroyed` holds
what died while the round was played, wreck or no wreck, and is cleared when the next round starts,
so each pickle carries one round's worth and nothing accumulates. Verified against an in-memory
replay of xke: 41 ticks, 0 disagree, 112 of 112 objects.

**The payload.** `GET /api/game/{game}/replay` is one fetch for the whole game, since playing 400
ticks must not be 400 requests. Per object: what it is, whose it is, and a row per tick it is known
for, keyed by `abs_tick`. One collection, so a sighting is an object whose rows are sparse and whose
heading was never known, and `contact` says so.

**Whose war it is.** `?faction=` decides what gets built, not what gets hidden: that side's own
objects as they were, and everything else only where its ships saw it. Nothing outside the side is
assembled, so nothing outside it can be read out of the JSON. The side comes from the login cookie:
a commander gets a side they fly, the director gets every side at once, and a director who has
switched to watching as a commander says so with `as_player`, which can only narrow. xke as the
director is 605 kB and 49 kB gzipped; as faction One, 184 kB and 15 kB.

**The playhead.** `lib/replay/` is a page rather than a mode of the map, because what the API serves
is the game's ground truth and the map is built around one player's picture. It shares the map's
camera and its shapes, which moved to `map/markers.js`, and has its own pointer handling since
nothing in a replay is draggable. `?page=replay&game=&tick=<abs>`, the tick written with
`replaceState` so playing a whole game does not put 400 entries behind the back button.

## Next

**Showing everything to a player** needs a game to be over, and there is no such state: archiving
moves the directory out of `games/` and `GamesRoot.holding` cannot see it, so "put it away" and "it
is finished" are one button. A `finished` flag in the game's settings is the smallest honest fix,
and the leaderboard wants the same flag. Its own GDDR: when a game is over, everyone sees all of it.

## Deliberately not

No recorder in the engine. A row is where something was and which way it pointed, with no condition
on it: hull tick by tick belongs in the panel beside the picture, as the snapshot's own reported
values rather than fields picked by name here. No explosions and no hit marks, until it is clear
from watching one what the picture is missing. A replay is read-only.