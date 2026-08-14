# 0022. A game's state is the root it is kept in

**Status:** Accepted

## Context

A game is now set up in four steps: name it and open registrations, let players put themselves
down, deal them into factions, then start it. So there is a stretch of time where a game exists,
has a name, and is collecting files, but cannot be played and must not appear anywhere a playable
game appears.

The same was already true at the other end of a game's life. Archiving solved it by moving the
directory somewhere else, which is why nothing that lists games has to filter: a game is playable
because of where it is.

## Decision

A game directory lives in exactly one place, a child of the data root:

    <data root>/games/<game>          being played
    <data root>/finished/<game>       over, and still open to everyone who played it
    <data root>/archived/<game>       out of sight
    <data root>/registering/<game>    named, collecting registrations, not started

`cfg.GamesRoot` holds a root and names its children, so the layout is written once and
`AdminService` carries one of these rather than a path it does arithmetic on.

**Where it is kept is what it is.** `GamesIn.active` says a round can still be planned there and
`GamesIn.readable` says a player can still open it, so no operation asks a game for a status and
none can disagree with the directory it is in. A game moves between `games/`, `finished/` and
`archived/` freely, in any direction.

It is the same directory throughout, holding the same kinds of file. `registering/` adds
`scenario.json`, saying which scenario it is being built from, and `registrations.jsonl`, holding
who signed up, what they named their ships and which faction the director put them in.

Moving between places is `shutil.move`. Starting a game moves it into `games/` and then
writes `ships.jsonl` and `settings.jsonl`. Putting it back into registration moves it out again and
deletes the roster, the round-zero pickle and the empty commands directory.

`game_names_in_use()` spans them all, so a name in registration cannot be claimed twice and the
move at the end cannot collide.

These are the stages of one game's life. A game a player runs on their own is not a stage of
it, and sits in a root of its own:
[0030](0030-solo-games-live-in-their-own-root.md).

The registrations travel with the directory and stay in the live game. They are a plan under
[docs/data.md](../data.md): the record of who asked for what, and nothing can rebuild it.

## Consequences

Every list stays a directory listing. `list_games`, `list_finished_games`,
`list_archived_games` and `list_registering_games` are the same function pointed at a different
root.

A game that has been started can go back into registration as long as no round has been played,
because nothing has been consumed yet. After the first round the roster is what people have been
playing, so it is refused.

The roots have to be created on demand, and a stray directory in any of them is a game. That
is the same bargain archiving already made.

## Alternatives rejected

**Games at the data root, with the other two beside it.** How it was first built: the root held the
games being played, and `archived/` and `registering/` were its siblings. Every path to a game that
is not in play then went up before it went down, and the three could not be ignored, moved or
backed up as one thing, having no parent of their own.

**A status field inside the game.** One directory, one `state` key, every list filtering on it.
Every reader then has to know the states, a reader that forgets shows half-built games to players,
and a game with a corrupt settings file becomes stateless rather than merely broken. Where a
directory sits cannot be forgotten by a caller.

**A separate signup store, keyed by scenario rather than by game.** The first draft: one open
signup per scenario, in its own format, with the game named later. It meant registrations had to be
copied into the game at start, the name could not be checked until the end, and two games from the
same scenario could not be prepared at once. Naming the game first makes the whole thing one
directory from the first click.

**A file per registration**, mirroring `ready/<player>.txt`, to avoid two players racing on one
file. Rejected in favour of one `registrations.jsonl`, because a game directory holding
`ships.jsonl`, `spawns.jsonl` and `settings.jsonl` should not sprout a subdirectory for a fourth
list. The race it guards against is two people registering in the same second, and losing one of
those is a re-click, not a corrupted game.
