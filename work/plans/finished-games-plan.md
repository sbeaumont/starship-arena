# When a game is over

A game runs until everybody stops caring. There is no way to say it is finished, so there is no
final score, nothing to put on show, and no reason a game from three engine versions ago should
still open. Four steps, in order, each shipping something on its own:

1. **Done.** A game is exported to a versioned text format, into Valhalla.
2. A game can be declared over, and moves there itself.
3. **Done.** Valhalla is a museum anybody can walk through.
4. A scenario says what "over" means, and the game declares itself.

The export went first because it needs nothing else: it reads a game that is being played and
writes a copy, so it was finished and tested before anything could be declared over.

## Valhalla is a root, not a flag

`archived/` means "over" today ([ADR 0022](../../docs/adr/0022-a-game-directory-moves-between-three-places.md)),
and it also means out of every list. Those are two different facts wearing one directory, which is
why there is nowhere to put a game that is finished *and* worth showing.

So Valhalla is a fifth root beside the other four, and archiving keeps only the half it is good at:

    <data root>/valhalla/<game>       over, and on show
    <data root>/archived/<game>       put away, out of every list

A root rather than a `finished` key in `settings.jsonl`, and 0022 already argued this out under
*A status field inside the game*: every reader would have to know the states, a reader that forgets
shows a finished game as playable, and where a directory sits cannot be forgotten by a caller.

It cost one enum member, and `GamesIn.Valhalla` is in. `GamesIn.planned` is already the question "is
a round being planned in here", so answering False for Valhalla is what stops the whole processing
machinery from touching a finished game - `playable()`, `process_due`, readiness, the cron - without
a single new check anywhere. That is the argument in one line: **nothing has to remember not to
process a finished game.**

## What exists to build on

`AdminService.archive_game` is the move, `shutil.move` and a collision check. Finishing is the same
function pointed at a different root, and unarchiving is the precedent for putting one back.

`GamesRoot.directory` resolves a *playable* game across the playing and solo roots. Reading a
finished one is `directory_in(GamesIn.Valhalla, game)`, which the replay path needs and nothing
else does.

`Replay` is the one thing that knows which saved world answers for a tick, and both the replay page
and the export walk it. They agree on nothing else: `GameReplay` answers to the map and changes with
it, so the export declares its own shape and reads the histories itself
([ADR 0034](../../docs/adr/0034-a-finished-game-is-exported-to-a-schema-of-its-own.md)).

`game_names_in_use()` spans the roots, so a name in Valhalla stays taken. That is what we want: a
finished game keeps its name forever.

## Step 1: the export, versioned. Done

`arena/app/valhalla/` holds one package per version: `v1/schema.json` is the definition,
`v1/from_engine.py` the translation, and both doors validate what goes through them.
`AdminService.export_to_valhalla` writes `valhalla/<game>/replay.json`, `arena.app.valhalla.load`
reads whatever version a file says it is and refuses the rest by number, and
`python -m arena.cli.main export <game>` drives it.
[ADR 0034](../../docs/adr/0034-a-finished-game-is-exported-to-a-schema-of-its-own.md) is the
discipline: **a version once written is never reinterpreted**, and the code adapts to the file.

It is a copy, not a move. Exporting a game that is still being played is how the format got tested,
and it is a readable backup of anything about to be archived.

v1 keeps more than the replay page draws, because a file's silence is permanent: hull, battery,
every component's reported status, the score earned, and who flew the ship. Scans stay out, so no
faction's fog of war can be rebuilt from a file, which is the one thing to remember before the
pickles of an exported game are deleted.

## Step 2: a game can be declared over

`finish_game` and `unfinish_game` on `AdminService`, exporting on the way in, and a button on the
console's Processing tab beside Archive.

A player's game list grows a second collection: the games they flew that are over. The API already
answers `games_for_player` off the playable roots, so this is one more root read, not a filter.

Where it bites: `archive_game` moves out of `games/` by name, so archiving something in Valhalla
needs it to move from wherever it is. Either finishing is one-way and you archive first, or the
move takes a source root. The second is honest and costs a parameter.

Valhalla holds a file per game rather than a game directory, so "moving there" is the export plus
whatever becomes of what is left behind. Deciding that is this step, not the last one.

## Step 3: the museum. Done

A Valhalla tab, open without a login, and the replay page pointed at any of it:
`?page=valhalla` lists what is in there, `?page=valhalla&game=<name>` plays one back.

**Anybody watches from any side**, which turned out to be the interesting half. The first plan was
every side at once and nothing else, on the grounds that a finished game has nobody left to keep
anything from. That is true and it makes a replay a diagram: the fog is the game, so v1 keeps the
scans and a museum game narrows exactly the way a live one does.
[GDDR 0035](../../docs/gddr/0035-a-finished-game-is-watched-from-any-side.md).

**It reads the export, not the pickles**, so the museum is not as fragile as the thing step 1
exists to fix. `arena/app/from_valhalla.py` turns a document into the same `GameReplay` the played
game builds, one builder per version, and the game UI never learns that a second source exists.
`test/app/test_the_museum.py` asserts the two agree for every side.

## Step 4: the game knows when it is over

Everything above is a director pressing a button. The last step is a scenario saying what over
means and the game answering for itself: a faction with nothing left in space, an objective taken,
a round limit reached.

This is the first real scenario trigger, and it is the machinery the story scenarios want
([ADR 0021](../../docs/adr/0021-scenarios-sit-in-the-services-layer.md) puts scenarios in the
services layer, which is where a trigger reading the world and moving a directory belongs - the
engine cannot move a game and must not know Valhalla exists).

A solo game is the customer that already exists: it runs until the player stops caring, and
"survive five rounds" or "kill all three pirates" is the smallest honest end condition in the game.

## What will bite

**A finished game must not be resurrectable by accident.** `unfinish_game` exists for the day
something is declared over by mistake, and it has the same shape as unarchiving. But a game that
has been exported and had its pickles deleted cannot go back to being played, and nothing stops
somebody pressing it. Either finishing keeps the pickles until the directory is archived, or
putting one back is refused once the pickles are gone.

**The leaderboard is waiting on a game being over, and nothing else.** A running game has no final
score. The export already carries what each object earned tick by tick, so what is missing is the
moment somebody says the numbers are final.

**0022 has to be edited, not superseded.** It says `archived/` means "over", and that stops being
true here. The convention is that a record is edited whenever the decision moves, and its title
counts three places while the code now knows five - 0030 already added a root by writing its own
record rather than renaming 0022, so Valhalla does the same and 0022's line about what archiving
means gets corrected.

**The export is a second reader of history**, and that is the price of it answering to nobody. Two
walks over the same snapshots, `game_replay` and `valhalla.v1.from_engine`, and a change to what a
snapshot holds has to be carried to both. Only one of them is allowed to lag: the file is what
somebody will still be reading in five years. `from_valhalla` is a third walk, and the one that
carries the fog rule, so it is held against `game_replay` by a test rather than by care.

**Exporting publishes a game.** Valhalla is open, so the button on the console makes both sides'
fog readable by anyone with the link, while the game carries on being played. Step 2 is where a
game stops being playable, and until then that is a thing the director has to know.