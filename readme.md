# Starship Arena

A recreation of a play-by-mail space combat game from 1991, rebuilt as something you can actually
play in a browser.

You command a starship. Every round you write ten ticks of orders: turn, accelerate, fire, scan,
cloak. Everyone hands their orders in, the round runs, and you find out together what happened.

The original was played by post. This one keeps the week-long rhythm and drops the envelope.

## What it looks like

The player's view is one tactical map. Your fleet, your faction's shared picture of the enemy, and
your course for the coming round as a chain of joints you drag:

```
tick 1 ──── 2 ──── 3 ──┐
                        4      drag a joint, and everything downstream
                        │      swings with it, clamped to what the ship can do
                        5 ──── 6
```

Dragging sets that tick's turn and acceleration. The client predicts the path exactly, because a
ship's own course is deterministic from its own orders. Point a weapon and you get its firing arc,
rotated to where the ship will actually be pointing at that tick.

Everything else follows from what your ships saw. A contact is a track of sightings, and its course
is inferred from the last two, because the game never tells you a target's true heading.

## Playing

Players get a link and open the map. The director runs a separate console: create a game, watch the
orders come in, process the round.

Ship statistics are public, all of them. The game is won by flying well.

## Running it

```bash
uv sync
bash arena-dev.sh          # api :8000, game UI :5173, console :8080
./arena-link.sh Serge http://localhost:5173 --director
```

Open the link it prints. That signs you into both halves.

```bash
npm run build --prefix game-ui
bash arena-serve.sh        # everything from one server on :8080, the way it deploys
```

## How it is built

A Python engine, a JSON API over it, a Svelte map for players and a Flask console for the director.
One WSGI application serves all of it, which is what lets it run on a host that offers exactly one.

Three things are worth knowing before reading the code:

**Rounds are deterministic.** A round is a pure function of the previous round's state and the
command files. No clock, no random numbers. That's why saved state can be deleted and rebuilt
rather than migrated, and why the console has a Regenerate button.

**Ships are built from components, configured by type objects.** A new ship model is one small
class, and it shows up in the reference, the new-game dropdown and the manual without any of them
being told.

**Components describe themselves.** They say what orders they take, what state they're in, and what
their type says they are. So the firing UI offers the right control for a weapon it has never heard
of.

## Documentation

[`docs/`](docs/) has the architecture, the glossary, the data formats and the deployment notes.
[`docs/adr/`](docs/adr/) has 18 decision records, each with what was rejected and why, which is the
part that stops the next person undoing it.

[`TODO.md`](TODO.md) is what's next.

## State of it

Playable and deployed. Games run, players plan, rounds process.

Logins, the console, the map, the planner, the ship reference and the round log all work. A
scenario builder, solid bodies to crash into, and a leaderboard are next.