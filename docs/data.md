# Game data

Everything lives in files under `GAME_DATA_DIR`, one directory per game, plus one registry file at
the root. There's no database.

```
<data root>/
    players.txt              who can log in, across all games
    <game name>/
        ships.jsonl          the plan: the roster the game starts from
        spawns.jsonl         the plan: arrivals the director scheduled
        commands/
            <ship>-commands-<round>.txt      the plan: what each player ordered
        status_round_<n>.pickle              the state: the world at the end of a round
```

## Plan and state

Every file here is one or the other, and which one decides everything about how it is written,
whether it can be thrown away, and who is allowed to touch it.

**A plan says what should happen.** The roster, the scheduled arrivals, the orders. Somebody wrote
it: a player typing commands, a director setting a game up or spawning a reinforcement. It is text,
it is authored, and it is added to rather than recomputed. Nothing can rebuild it, so it is
irreplaceable and tracked in git for the test games.

**State is what did happen.** The world at the end of each round: everything in space, the
graveyard, and what has arrived. Nobody writes it by hand. It is a pickle, it is rewritten whole
every round, and it can always be rebuilt by replaying the plans, because [the game is
deterministic](architecture.md#processing-a-round). So it is gitignored and disposable.

The test that decides which one a new file is: **could the engine produce it again from what is
left after you delete it?** If yes it is state. If no it is a plan, and losing it loses the game.

Two consequences worth spelling out, because both have caught us:

**A thing that happens must be in exactly one plan.** A ship the director schedules goes in
`spawns.jsonl`, because nothing else records that instruction. A ship a starbase's spawner creates
does *not*, because the Fire order that created it is already in a command file, and a second
record would produce two ships on a replay.

**State must never be the only home for anything.** Anything written into the world and nowhere
else survives exactly until the next regenerate.

## Regenerating

When saved state stops matching the code, delete it and rebuild. Never write a compatibility shim
to read an old shape. The console's **Regenerate** button does exactly this: drop the pickles,
re-run setup, replay every round up to where the game was.

Regenerating a game that has been running against older engine code will produce different combat
outcomes. Same plans, but the rules have moved.

## ships.jsonl

One JSON object per line, no header. `#` starts a comment.

```jsonl
{"name": "BaseOne", "type": "SB2531", "faction": "One", "player": "TeamOne", "x": 548, "y": 116}
{"name": "Voyager", "type": "A2527", "faction": "One", "player": "Rik", "x": 479, "y": 121}
```

`name`, `type` and `faction` are required. `type` is a type name from the ship registry, `A2527`
rather than `A2527 Alligator`.

`x` and `y` are optional. Leave them out and setup spreads the factions evenly around the origin,
then writes the coordinates back into this file so the placement replays.

`player` is optional, and a ship without one is nobody's: no orders are expected and it is not
player controlled.

An absent field is why this is JSON rather than columns. Positional whitespace has no way to say
"this ship has no player" without shifting every field after it.

**`player` is an identity, not a label.** It's the name someone logs in with, so a typo creates a
commander who can never sign in. The new game screen autocompletes it for that reason.

## spawns.jsonl

Arrivals the director scheduled. Same format, one object per line, added to and never rewritten:
a line is one instruction that was given.

```jsonl
{"round": 3, "tick": 1, "name": "Voyager-2", "type": "A2527", "faction": "One", "player": "Rik", "x": 479, "y": 121, "heading": 90}
```

`round` and `tick` are when it appears, and are what make a replay put it back in the same place.
`player` and `faction` are optional, `heading` and `speed` default to 0.

The file is absent until something is scheduled.

A ship arriving in round N takes its first orders in round N+1: it is not in the world when round
N's readiness is checked, so nothing waits for orders it could not have written.

## settings.txt

Optional, per game. `key value` per line, `#` starts a comment.

```
process_hours 8 20
process_on_all_ready yes
```

`process_hours` are the hours of the day at which the round is processed whether the orders are in
or not. `*` means every hour. Absent means the director processes it. The timing comes from cron
running `arena-cron.sh` on the hour; nothing here measures elapsed time.

`process_on_all_ready` processes the moment the last player says they are ready.

## ready/

One file per player, so two of them saying ready at once cannot race.

```
ready/Menno.txt      Round 4 Ready
```

A line per round they have declared themselves done with. Unreadying removes the line. This is a
separate signal from having saved orders: you can save a plan and keep thinking about it.

## Command files

One per ship per round, named `<ship>-commands-<round>.txt`. A ship without one for the current
round blocks the whole round from being processed.

```
1: R10
2: R15
2: A-4
3: Fire R1 90
```

`<tick>: <command>`. A weapon takes one order per tick.

## players.txt

At the data root, not inside a game, because a player's name is their identity everywhere.

```
Name    Token                   Role      Active
Dennis  3R5iNHN5ROLvLG3VpoMocQ  player    yes
Menno   T7bAvKQEr4tRNMbF-EJ6Rw  player    no
Serge   Br-A2Ly1XYYF65yHFo2cQA  director  yes
```

Same shape as the old column files. Gitignored, because the tokens are secrets.

Columns are read by position, and a field is split off on whitespace, so an empty one would
collapse into the gap between its neighbours. Every column is therefore written out: an ordinary
player has the role `player`, not a blank. A file from before a column existed is still read, with
the missing column taking its default, so adding one costs nothing.

A name holds no spaces, and one typed with them is stored with underscores instead. It is a column
here, a field in `ships.jsonl`, and part of a filename (`ready/<player>.txt`), so it has to survive
all three. Looking a name up accepts either spelling.

`Active` is `no` for someone deactivated: they keep their name, and old games still name them, but
no token of theirs resolves to anyone and the new-game screen does not offer them. Distinct from
revoking, which takes the row away and frees the name.

A token is a long random string standing for the person holding it: it goes out in a link, comes
back in a cookie, and is what an interface trades for an identity. Kept in plain text so a link can
be sent again, and hand-editable so you can always get yourself back in.

Issuing a token again replaces the old one, which is also how a leaked link is dealt with.