# Glossary

The words the code uses. Using different ones in a UI, an API field or a commit message is how
vocabulary drifts.

## Time

**Tick.** One step of simulation. `Tick(round, tick)` where tick runs 1 to 10, plus `abs_tick` for
ordering across rounds. Everything an object does happens in a tick, in the phase order set by
`GameRound.do_tick`.

**Round.** Ten ticks, and the unit players plan in. Orders are written per tick, submitted per
round.

**Last round.** The newest round that has been processed. **Current round** is that plus one: the
one being planned now. Those are the only two names for it. Never "orders round", never "picture
round", and never store both when one is the other plus one.

## The world

**Object in space.** Anything with a position: ships, missiles, mines, and later asteroids and
worse. The base of everything in the simulation.

**Owner.** A reference to an object in space, never to a person. A missile's owner is the ship that
fired it, a mine's is the ship that laid it, and **a ship's owner is itself** (`Ship.__init__`
passes `owner=self`). Warheads and scoring reach a faction through it, which is how anything a ship
puts into space knows whose side it is on. The person is the *player*, and only a ship has one.

**Machine.** An object that was built, so it has hull, battery and components. Ships, starbases,
missiles and mines are machines.

**Type, or model.** What a machine is: `A2527`, readable as `A2527 Alligator`. A type object holds
the maxima and the set of components, and instances ask it rather than knowing themselves.

**Component.** A part a machine is built from: shields, a laser, a launcher, a scanner, a cloak.
Components answer for their own orders and their own state.

**Category.** The family an object belongs to: `Ship`, `Starbase`, `Missile`, `Mine`. Where a type
is the model, the category is the kind of thing, and interfaces key off it so they never need a
list of type names.

## Playing

**Commander, or player.** A person. Their name is their identity in every game and the name they
log in with.

**Fleet.** The ships one player commands in a game. Several ships is normal, and a player's view
plans all of them together in one map.

**Director.** The person running the games. One role, marked in `players.jsonl`, and the only one
the console lets in.

**Faction.** A side. Every ship belongs to one, and fog of war is shared across it. A fleet is
usually all in one faction, though a player with ships in two is supported.

**Order.** One line of a command file: `<tick>: <command>`, for example `3: Fire R1 90`. A weapon
takes one order per tick.

**Score.** Points for damage done: half a point per point of shield taken down, a bonus for
breaking one, a point per point of hull, and a bonus for a kill. You score nothing for hitting your
own faction.

## What is recorded

**Snapshot.** What an object was, at one tick: position, heading, speed, hull, battery and what
every component reported. Values, never references, so a snapshot stays true after the round moves
on.

**History.** All of an object's snapshots and events, keyed by tick, attached to the object.
`TickHistory` is one tick of it.

**Event.** Something that happened to an object during a tick, with a `kind`: `internal`, `hit`,
`explosion` or `scan`. Everything except scans shows up in the player's log.

**Contact.** Something a faction has scanned but does not own, as a track of sightings. A scan
records where something was, never its heading, so a contact's course is inferred from its last
two sightings and single sightings have no course at all.

**World.** Everything an object can ask about the game beyond itself: what is in space, and the
graveyard. Passed down every engine hook, saved whole once per round, and where anything
world-spanning goes when it is added later.

**Graveyard.** Destroyed ships and starbases, kept so their score still counts and whoever was
flying them can look back at their history. Part of the world, so each round holds the graveyard as
it stood at the end of that round. Spent ordnance is not kept: a machine says whether it
`leaves_a_wreck`, and only ships do.