# 0030. A solo game is a game in a root of its own

**Status:** Accepted

## Context

Somebody who registers a name today gets an empty list and a sentence saying the director will
add them to a game. They wait days for a game to be set up, and when it starts they are learning
the map, the orders and the weapons against people who already know all three.

Everything needed to fly a round already exists. The map plans it, `process_on_all_ready`
processes it the moment everyone has said they are done, and a ship with no player needs no
command file. What was missing is a game to do it in.

A game directory lives in one of the roots ([0022](0022-a-game-directory-moves-between-three-places.md)),
and each is a stage of one life: collecting registrations, being played, over. A practice
game is not a stage of that. It is a second kind of game, with the same files in it.

## Decision

A fourth root, beside the other three:

    <data root>/solo-games/<game>          somebody's own

One per player, named `Solo_<player>`, so the name says whose it is and there can only be one.
Starting another throws away the one they had.

`arena/app/scenarios/solo.py` builds it: the one or two hulls the player picked, three pirate
hulls drawn from the registry, and the standard five asteroids that the game is fought over. Its
settings are `process_on_all_ready` with no hours and no announcement, so saying ready runs the
round and nobody else hears about it.

**`GamesRoot.holding(game)` says which of the two playable roots a game is in**, and
`_EngineAccess._gd` asks it. That single resolution is what lets one set of operations serve both:
a solo game is planned, ordered, made ready, processed and journalled through exactly the calls a
shared game is, and nothing above the seam learns there are two kinds.

**A shared game may not take a solo name.** `AdminService._claim_name` refuses anything starting
with `Solo`, and refuses a name already used by a game being played, archived, registering or
somebody's own. Player names are unique, so one reserved word speaks for every solo name whether
or not anybody has started one.

A solo game appears in no list of games. `list_games` spans `games/` only, `Me.games` with it, so
the director's console and the scoreboard never fill up with other people's practice. The player
asks for theirs by itself, at `/api/game/solo`, and the games screen puts it under its own header.

## Consequences

The whole player-facing surface works on a solo game without knowing it exists: the plan, the
orders, the ready flag, the pulse, the overview, the journal, regenerate. Adding the scenario and
two API routes was the whole of it.

`GameService` now creates and deletes a game directory, where before it wrote command files and
ready flags. That is a real step up in what the player-facing service may do, and it is bounded by
the two things it cannot choose: the root is `solo-games/`, and the name is derived from whoever
the cookie says is asking. `PlayerRegistry.issue` now refuses a name holding `..` or a slash, so
that derived name cannot walk out of the root. A single dot stays legal, because St. Nicolaas is a
name somebody will want.

Reserving `Solo` costs the director the word. No shared game can be called "Solo Mission".

The console gains no page. A director tests this by starting their own, and a stray directory in
`solo-games/` is somebody's game, which is the bargain the other three roots already made.

The three pirates drift. They are scanned, they are shot at, and nothing shoots back, so a solo
game today teaches the controls rather than the fight. Making them fly is the NPC work, not this.

## Alternatives rejected

**A flag inside the game**, `solo: true` in `settings.jsonl`, with every list filtering on it.
This is the "status field inside the game" that [0022](0022-a-game-directory-moves-between-three-places.md)
already rejected, and it fails the same way: every reader has to know the flag, a reader that
forgets shows a stranger's practice game on the director's console, and a game whose settings file
will not parse stops being solo rather than being merely broken.

**Solo games in `games/`, told apart by their name.** The name is already `Solo_<player>`, so the
prefix looks free. It reads a filing convention as a rule, the same defect as deriving a faction
from the registry module it is declared in ([0021](0021-scenarios-sit-in-the-services-layer.md)).
A director who names a game `Solo_Mission` then silently changes what it is.

**Precedence between the roots**, with `games/` winning a name clash. Built first, and it put a
rule in `holding()` for a situation that reserving the prefix makes impossible. The rule was also
invisible at the moment it mattered: the director typing the clashing name saw nothing, and found
out when somebody's practice game answered instead of theirs.

**A sandbox that is not a game**: a world built in memory, ten ticks run, nothing written down. It
needs its own processing path, its own API and its own map wiring, all of it parallel to the real
one and free to drift from it. And the player cannot come back to it tomorrow, which is most of
what makes a first game worth playing.

**Creating one automatically at first login.** Every name that ever registers gets a directory,
including the ones that never come back. Worse for the player: they are given a hull instead of
picking one, and have to throw a game away before they can fly what they wanted.