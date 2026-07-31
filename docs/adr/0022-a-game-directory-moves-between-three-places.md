# 0022. A game directory moves between three places

**Status:** Accepted

## Context

A game is now set up in four steps: name it and open registrations, let players put themselves
down, deal them into factions, then start it. So there is a stretch of time where a game exists,
has a name, and is collecting files, but cannot be played and must not appear anywhere a playable
game appears.

The same was already true at the other end of a game's life. Archiving solved it by moving the
directory to `archived/` beside the data root, which is why nothing that lists games has to filter:
a game is playable because of where it is.

## Decision

A game directory lives in exactly one of three places:

    <data root>/<game>          being played
    archived/<game>             over
    registering/<game>          named, collecting registrations, not started

It is the same directory throughout, holding the same kinds of file. `registering/` adds
`scenario.json`, saying which scenario it is being built from, and `registrations.jsonl`, holding
who signed up, what they named their ships and which faction the director put them in.

Moving between places is `shutil.move`. Starting a game moves it into the data root and then
writes `ships.jsonl` and `settings.jsonl`. Putting it back into registration moves it out again and
deletes the roster, the round-zero pickle and the empty commands directory.

`game_names_in_use()` spans all three, so a name in registration cannot be claimed twice and the
move at the end cannot collide.

The registrations travel with the directory and stay in the live game. They are a plan under
[docs/data.md](../data.md): the record of who asked for what, and nothing can rebuild it.

## Consequences

Every list stays a directory listing. `list_games`, `list_archived_games` and
`list_registering_games` are the same function pointed at a different root.

A game that has been started can go back into registration as long as no round has been played,
because nothing has been consumed yet. After the first round the roster is what people have been
playing, so it is refused.

The three roots have to be created on demand, and a stray directory in any of them is a game. That
is the same bargain archiving already made.

## Alternatives rejected

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
