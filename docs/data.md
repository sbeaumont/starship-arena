# Game data

Everything lives in files under `GAME_DATA_DIR`, one directory per game, plus one registry file at
the root. There's no database.

```
<data root>/
    players.jsonl            who can log in, across all games
    <game name>/
        ships.jsonl          the plan: the roster the game starts from
        bodies.jsonl         the plan: the terrain the game is played over
        spawns.jsonl         the plan: arrivals the director scheduled
        settings.jsonl       the plan: when this game processes a round
        registrations.jsonl  the plan: who put themselves down, and for how many ships
        scenario.json        the plan: which scenario it is being built from
        commands/
            <ship>-commands-<round>.txt      the plan: what each player ordered
        status_round_<n>.pickle              the state: the world at the end of a round
```

Two sibling directories hold game directories that are not in play. `archived/` is a game that is
over, `registering/` is one that has been named and is collecting registrations. A game directory
is the same thing in all three places, and moving between them is a `shutil.move`.
[ADR 0022](adr/0022-a-game-directory-moves-between-three-places.md).

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

## bodies.jsonl

The terrain, one object per line. Optional: a game without one is played on empty space.

```jsonl
{"name": "Asteroid-1", "type": "Asteroid", "x": 0, "y": 250}
{"name": "Asteroid-2", "type": "Asteroid", "x": 238, "y": 77}
```

`type` is a type name from the body registry. All four fields are written, because nothing places a
body for you: coordinates are never generated and never written back, so the file it came from is
already the record a replay needs.

A scenario is what puts them there. `FiveFactionWar.bodies()` returns a ring of five at radius 250,
written when the game starts.

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

## settings.jsonl

Optional, per game. One JSON object, on one line.

```jsonl
{"process_hours": [8, 20], "process_on_all_ready": true}
```

`process_hours` are the hours of the day at which the round is processed whether the orders are in
or not. Empty means the director processes it. The timing comes from cron running `arena-cron.sh`
on the hour; nothing here measures elapsed time.

`process_on_all_ready` processes the moment the last player says they are ready.

## registrations.jsonl, and scenario.json

While a game sits in `registering/`, `scenario.json` says which scenario it is being built from and
`registrations.jsonl` collects who wants in.

```jsonl
{"player": "Menno", "names": ["Rocinante"]}
{"player": "Rik", "names": ["Voyager", "Pathfinder"], "faction": "Feline"}
```

A name per ship, so the number of names is the number of ships asked for and there is no second
field to disagree with it. How many you may ask for is the scenario's answer, not this file's.

A ship name has to be free across the whole game, so a clash is refused while the person who typed
it is still there to change it.

`faction` is where the director dragged them on the assignment screen. Absent means still in the
pool, and the deal places them. It is written every time the screen is saved, so leaving the screen
and coming back shows the columns as they were.

Both files travel with the directory when the game starts. They are a plan: nothing can rebuild
the record of who asked for what, and the roster screen reads the registrations to know which names
a ship may belong to.

## The name on disk, and the name you read

A game is named by a person and stored as a directory, so `Faction War  2` becomes
`Faction_War_2`. Runs of whitespace collapse to one underscore, and the name shown anywhere is that
name with the underscores turned back into spaces.

The display name is therefore derived and never stored. Two fields for one name is two things that
can disagree, and the one on disk has to win because it is the directory.

`arena/app/naming.py` holds both halves. Nothing else transforms a game name.

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

## players.jsonl

At the data root, not inside a game, because a player's name is their identity everywhere.
Gitignored, because the tokens are secrets.

```jsonl
{"name": "Dennis", "token": "3R5iNHN5ROLvLG3VpoMocQ"}
{"name": "Menno", "active": false}
{"name": "Serge", "token": "Br-A2Ly1XYYF65yHFo2cQA", "role": "director"}
```

Only `name` is required. `token` absent means no link has been issued, `role` defaults to
`player`, `active` defaults to true. Writing only what differs from the default keeps a line
readable, and it is what lets somebody exist here with no token at all.

That last part is why this is JSON rather than columns. A tokenless row cannot be written in
positional whitespace: the empty field collapses into the gap and the role is read as the token.
Which meant a name known only from a game's roster had nowhere to record that it had been put
aside.

`active: false` is someone deactivated: they keep their name, old games still name them, and
nobody else can claim it, but no token of theirs resolves to anyone and the scenario screens do
not offer them.

Three things you can do to a row, and they are separate on purpose. **Removing the link** clears
`token` and keeps the person. **Deactivating** sets `active` and keeps everything. **Removing**
takes the row away and frees the name.

**This file is the whole list.** Game rosters are not consulted to build it, so a name is here
because somebody put it here and removing it removes it. A ship in a game can still name someone
who has no row, and nothing on the players page will say so; the game's own page is where you see
who commands what.

Hand-editable on purpose: this file is how you let yourself back in when locked out.

A token is a long random string standing for the person holding it: it goes out in a link, comes
back in a cookie, and is what an interface trades for an identity. Kept in plain text so a link can
be sent again, and hand-editable so you can always get yourself back in.

Issuing a token again replaces the old one, which is also how a leaked link is dealt with.