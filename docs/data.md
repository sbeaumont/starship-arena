# Game data

Everything lives in files under `GAME_DATA_DIR`, one directory per game, plus one registry file at
the root. There's no database.

```
<data root>/
    players.txt              who can log in, across all games
    <game name>/
        ships.txt            the roster: who commands what, and where it started
        commands/
            <ship>-commands-<round>.txt
        status_round_<n>.pickle
        graveyard.pickle
```

## What is precious and what is not

**The text files are the game.** `ships.txt` and the command files are what a player wrote and
what the director set up. They're tracked in git for the test games, and they're irreplaceable.

**The pickles are derived.** They hold the state at the end of each round, and they can always be
rebuilt by replaying the command files, because [the game is
deterministic](architecture.md#processing-a-round). They're gitignored.

So when saved state stops matching the code, delete it and regenerate. Never write a compatibility
shim to read an old shape. The console's **Regenerate** button does exactly this: drop the pickles,
re-run setup, replay every round up to where the game was.

Regenerating a game that has been running against older engine code will produce different combat
outcomes. Same commands, but the rules have moved.

## ships.txt

Whitespace separated, a header line naming the columns, `#` starts a comment:

```
     Name   Type Faction    Player    X    Y
  BaseOne SB2531     One   TeamOne  548  116
  Voyager  A2527     One       Rik  479  121
```

`Type` is a type name from the ship registry, `A2527` rather than `A2527 Alligator`.

`X` and `Y` are optional. Leave them at 0 and setup spreads the factions evenly around the origin,
then writes the coordinates back into this file so the placement replays.

Nothing here may contain a space, since the file is split on whitespace. Names are cleaned with
underscores rather than rejected.

**`Player` is an identity, not a label.** It's the name someone logs in with, so a typo creates a
commander who can never sign in. The new game screen autocompletes it for that reason.

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
Name    Token                   Role
Dennis  3R5iNHN5ROLvLG3VpoMocQ
Serge   Br-A2Ly1XYYF65yHFo2cQA  director
```

Same shape as `ships.txt`. Gitignored, because the tokens are secrets.

A token is a long random string standing for the person holding it: it goes out in a link, comes
back in a cookie, and is what an interface trades for an identity. Kept in plain text so a link can
be sent again, and hand-editable so you can always get yourself back in.

Issuing a token again replaces the old one, which is also how a leaked link is dealt with.