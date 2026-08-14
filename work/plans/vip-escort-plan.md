# VIP escort

One side gets a VIP hull across the map to a beacon. The other side kills it.

## 1. Closing a game. Done

A `finished/` root: locked, still open to whoever played it. `GamesIn.active` gates planning and
processing, `GamesIn.readable` gates opening. A game moves between `games/`, `finished/` and
`archived/` in any direction. [ADR 0022](../../docs/adr/0022-a-game-directory-moves-between-three-places.md).

## 2. A game knows its scenario

`scenario.json` is written by `open_registrations` into `registering/` and read from there, so a
started game cannot say what built it and `create_game` never writes one. Write it in
`_build_game`, read it from the game's own directory.

## 3. Occlusion. Done

[GDDR 0038](../../docs/gddr/0038-terrain-blocks-what-you-can-see.md). `World.blocks_sight`, asked
by `can_scan` after the range check. Lasers come free through `can_fire_at`. Explosions are not
blocked. Terrain is never scanned and goes into the plan, the replay and Valhalla from the world.

20 ships over 70 rocks process a round in 0.4s.

## 4. The scenario

**Map.** 1800 by 900, thirds of 600. Escorts start as a group in the west third, north or south by
the draw. Hunters as a group in the middle. Beacon anywhere in the east third, 100 clear of its
edges. 60 to 80 asteroids over the whole board, radius 25.

Two rngs: seeded for the asteroid scatter, open for placement. The scenario keeps the seeds worth
playing and can draw a fresh one.

**Beacon.** A small body. Arriving is docking, `range` 10 and `max_approach_speed` 10, as
`Replenisher` has it. Visibility 40. Notices in `post_move` and records that a ship docked.

The escort is briefed on where it is and the hunters are not: `charted_for(world, factions)`,
asked when a player's picture is built. Terrain is on everybody's chart by rule; this is a
scenario adding to that for one side.

**Scoring.** Combat score unchanged. Objective points are the scenario's award: 500 across the
escort players when the VIP docks, 500 to the hunters when it dies, written as the game closes.

**Roster.** Escort and Hunters, registering, two ships a player, director assigns.
`_deal_players` spreads the rest. The VIP goes on the roster like any other ship.

**Hull.** `civilian.py` in the registry.

```
max_speed 30, max_turn 60, max_delta_v 20
max_hull 90, shields 90 a quadrant
generators 10, start_battery 150
max_scan_distance max_scan(25)
Cloak('C1', 3)
Launcher('M1', EMPMine(), 6, (135, 225))
```

`EMPMine` is new: `NanocyteMine`'s shape with `EMPWarhead`.

**Ending it.** `VipEscort.outcome(world)`, asked by `_settle` after every processed round:
`beacon.docked` holds the VIP, or the VIP is destroyed. It writes `outcome.json` and finishes the
game. A scenario that never ends by itself answers None.

Not in Valhalla. The export is a numbered schema and carrying the outcome means a version of it.

## 5. Messaging

Version 1.1. A panel sharing the log bar, sliding open the way the log does. Director broadcasts
each round, commanders to each other later. Until then the escorts get their rough idea of where
the beacon is out of band.

## Open

- Asteroid count and radius are a guess.

## Later

- Fleeing and evading as a `Controller` beside `Pilot`.
- An interface for an agent to fly ships.