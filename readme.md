# Starship Arena

The game is played in rounds, and every round consists of 10 ticks (1-10).
For a full description of gameplay, see [the starship-arena-manual](./starship-arena-manual.pdf).

## Development instructions

This version has been developed with Python 3.10. You'll need to set up you environment with:

- Python 3.10 (or higher)
- weasyprint
- Jinja2
- Pillow
- Flask

The command-line entrypoint of this project is `./main.py`.

`python main.py [setup, generate, manual, send]`

This project can also be hosted as a Flask project with a Web UI.

`flask --app flask_app run --debug`

Watch out you don't use the debug flag in an unsafe environment.

## Overall Architecture

There are two entry points: the CLI in main.py, and the web app in flask_app.py.
The main packages are:

- engine: executes a round plus game directory and command features
- ois: the game objects and their behavior
- rep: generating the reports, mostly for the CLI, but also has the 
important history and visualize packages also used in the webapp.

Persistence is based on simple pickle files which turn our to be surprisingly useful
and robust in this case. Each round leads to a generated pickle file with the status of
all objects until that time. These pickle files are used both by the engine to intitialize
itself at the start of the round, the PDF generator to generate results, but also by the 
web interface to present all information.

The web interface consists of flask_app, appfacade and specific templates (some templates
are for the PDF generator).

Some notable architectural choices:
- Commands are implemented with a Command pattern.
- Parameters to the commands are more complex than you may expect, but this is needed
to allow the web interface to offer validation while the player is creating their commands
for the next round.
- The History and TickHistory objects are an object's "memory", allowing all the reporting
capabilities in the game to generate the history, graphics, etc.
- The main game objects are composed of component objects to allow flexible creation of new
space ships, missiles, etc.
- Game objects are implemented as object - type object pairs that configure a specific instance
of a game object. The type object knows the specific components a game object should have. This
is how it's very easy to come up with a new ship or missile design and add it to the registry.
- AppFacade is intended to shield the web app (flask_app.py) from knowing how too much of the
internals of the rest of the code base.

## Todo

- [x] Allied ship paths drawn in green 
- [ ] A predictive graphic in the plan round screen
- [ ] Utilities like repair droids
- [ ] Objects like black holes and gas clouds, nebulae
- [ ] Scenario mechanism
- [ ] (NPC) Pilots and Gunners. Programmable / commandable?
- [ ] Security system to allow unique player logins
- [ ] Game master, player and admin roles
- [ ] Message of the Day
- [ ] Message of the round, possibly tied to scenario
- [ ] Scanner that reveals internal details of ships like ammo and energy levels.
- [ ] Damage to components
- [ ] Point defense, possibly tied to an NPC gunner?
- [ ] Fix the crash in a malformed Boost command
- [ ] Allow in-game spawning. Maybe an admin command file? Probably related to scenarios.
Respawning after death could also be a thing.
- [ ] Race condition problem when launching missiles: Weapons fire in post move, which leads 
to the common occurrence that all 
fired rockets blow up when the ship gets hit in the same tick (they're in space but didn't move yet). 
Move weapon firing to pre_move? Or weapons fire after existing objects explode. Another problem that
there is now an ordering problem. It depends on if a ship executed its fire command before or after a
missile does its post move step. If the ship was before, the fired missiles are placed in space and will 
explode. If the ship was after the missile in the list the fired missiles are not in space yet and will
not explode. The game is built on the premise that the order of processing each object must never matter
so this needs to be fixed.
