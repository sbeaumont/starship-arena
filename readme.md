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