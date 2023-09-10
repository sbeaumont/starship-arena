# Starship Arena

The game is played in rounds, and every round consists of 10 ticks (1-10).
For a full description of gameplay, see [the starship-arena-manual](./starship-arena-manual.pdf).

## Development instructions

This version has been developed with Python 3.10. You'll need to set up you environment with:

- Python 3.10 (or higher)
- weasyprint
- Jinja2
- Pillow

The entrypoint of this project is `./main.py`.

`python main.py [setup, generate, manual, send]`

## Todo

- [x] A full energy system. Many things should cost energy, but now there are no implications for energy use.
- [x] More weapon types, ship types
- [x] Factions
- [ ] Utilities like repair droids
- [x] Special scans
- [x] Cloaking / Anti Detection Systems
- [ ] Other objects like black holes and gas clouds
- [x] Energy cost for current weapons, shields and movement.
- [x] Shields, including boosting them
- [x] Star bases, including replenishment
