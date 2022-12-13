# Starship Arena
## Development installation

This version has been developed with Python 3.10. You'll need to set up you venv with:

- Python 3.10
- weasyprint
- Jinja2
- Pillow

The game is played in rounds, and every round consists of 10 ticks (1-10).

## Stuff that isn't implemented yet
- A full energy system. Many things should cost energy, but now there are no implications for energy use.
- Shields. Every hit goes straight to the hull
- More weapon types, ship types
- Star bases, docking, repair
- Factions
- Utilities like repair droids
- Special scans
- Cloaking / Anti Detection Systems
- Other objects like black holes and gas clouds

## Commands
You send commands in a .txt file. Enter one command per line, with the format `(tick number): (command)`.
You can write multiple commands for a tick, but they each should be on their own line. Whitespace in the commands does
not matter: you can write R 90 or R90, whatever is your preference.


All commands are relative commands. Turning x degrees with respect to current heading, acceleration changes current
speed by x amount, etc.


The following commands let the ship turn 90 degrees left and accelerate by 25 on tick 1,
and fire a rocket 90 degrees from its current heading on tick 2:

    1: L90
    1: A25
    2: Fire Launcher1 90

It does not matter in which order you put these lines, and it also does not matter if the tick numbers of the lines are out of order.
All orders get processed in tick number order, and within a tick orders get processed in a specific order. Empty lines are ignored.

If you give multiple turn or accelerate commands in a single **tick**, they get combined (added) into one combined command.
If you turn beyond the maximum turn rate of the ship, the command gets constrained to the maximum. The same goes for maximum acceleration and speed.

You can fire each weapon once per tick, and they might have temperature or ammo to take into account.
If you multiple commands to fire a specific weapon in the same tick, only the first command is executed. In this case line order does matter.

- `R<degrees>`: turn right by x degrees (e.g. `R45`).
- `L<degrees>`: turn left by x degrees (e.g. `L20`)
- `A<units>`: accelerate or decelerate (negative e.g. `A-20`). Ships can equally go forwards and backwards. Note that if you have 0 speed you can turn as much as you want.
- `F`/`Fire <Weapon Name> <Direction or Target>`: Fire a weapon. Lasers need the name of the target, rockets get fired in a relative direction (e.g. `Fire Laser1 MasterBlaster` or `F Launcher1 -45`). This command does need whitespace to separate the parameters.

## Tick execution order
All ships and other objects performs each step simultaneously.

1. Generators generate energy
1. Weapons and utilities update (e.g. lasers cooling down)
1. Player ships execute pre-move commands
   1. Accelerate / Decelerate
   1. Turn (Decelerate before turn allows fast turning in one tick)
1. All move to new location by heading and speed
1. Player ships execute post-move commands
   1. Fire weapons
1. All scan environment
1. Non-player controlled objects like rockets perform actions
   1. Check for proximity & explode
   1. Turn and accelerate (rockets towards closest target if scanned)

## Weapons
### Lasers
Lasers are fired at a specific ship and always hit if they are in range. Lasers heat up per shot and can't fire at their maximum temperature.

Lasers always heat and use energy when fired, even when there's no target, so don't just spam fire commands!

Current stats:

        max_temperature = 100
        energy_per_shot = 5
        damage_per_shot = 10
        heat_per_shot = 20

### Missiles
Missiles are fired in a direction and scan a cone in front of them. They will target the nearest object they see, but not the firing ship or its rockets. However, when the rocket explodes, it damages everything in range, including its origin ship and rockets.

A rocket launcher has a limited amount of ammo.

Current stats:

         initial_load = 5

Rocket stats:

    max_speed = 60
    explode_distance = 6
    explode_damage = 10
    scan_distance = 150
    scan_cone = 45
    max_battery = 125
    hull = 1

Rockets will get destroyed by any damage. They have no maximum turn rate, and are smart enough to 
predict their target's next location, and reduce their speed to not overshoot their target. When these buggers
lock on, they're fearsome.

Rockets will target other rockets, so shooting a rocket is one of the best ways to defend against them.

## Ships
Player controlled war machines

Current stats:

    max_delta_v = 25
    max_speed = 45
    max_turn = 35
    generators = 8
    max_battery = 500
    start_battery = 125
    hull = 100

### Energy use

- Every tick the ship uses speed / 10 energy. 