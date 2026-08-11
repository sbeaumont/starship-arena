# 0032. A starbase replenishes you, and picks who

**Status:** Accepted

## Context

Replenishing was the ship's own order. `Rep` took no selector and no parameters: the ship asked the
world for anything that could restock it, took the first one it found, and was refilled if it
happened to be within 10 units at a speed of 10 or less.

Three things were wrong with that, and only the first is a bug.

It searched the world and stopped at the first answer whether or not that one worked, so a fleet
with two bases could sit alongside the second one and never be served, and never be told why. It
never asked whose base it was, so an enemy base restocked you as readily as your own. And a
starbase giving the order found *itself* in range at speed 0, which is a full repair, every tick,
for free.

The interface made the same point from the other end. Every order in the game addresses a
component, which is what lets the map offer a control for one without knowing what it is. Replenish
addressed the ship, so it fitted none of that machinery and had no control in either shell: the
only way to give it was to hand-write a command file. It sat on the backlog as "Replenish has no
control" for exactly as long as it was a ship order.

Meanwhile a starbase's commander has a seat with very little in it. They cannot move, they shoot,
and they have three replacement hulls to spend over a whole game.

## Decision

**A starbase restocks a ship, and names which one.** The order is `Rep RP <ship>`, addressed to a
`Replenisher` component the base carries, alongside its lasers and its spawner:

| | |
|---|---|
| reach | 10 units |
| the ship's speed | 10 or less |
| how many | one ship per tick, per replenisher |
| what it costs | nothing, and there is no limit over a game |
| what it gives | full hull, full battery, every shield quadrant, every laser cooled, every magazine |

**A restock never takes anything away.** Anything already better than a fresh one keeps what it has,
so a quadrant boosted to twice its maximum comes through the order meant to help it with the boost
intact. Boost above the maximum still dissipates at the end of the round, as it always did: the
replenish does not spend it, the round does.

**It is never asked whose ship it is.** A commander may restock the other side. Colluding costs
them the tick their own fleet wanted, and it is visible: both ships write the exchange into their
logs, so a faction can read what its base did on its behalf.

What it will not do is restock the base it is mounted on. Docking with yourself is not a
manoeuvre, and a base that could do it would repair 250 hull and 1600 of shield every tick it was
not otherwise busy.

The word `Rep` stays in the order language as a second spelling of `Fire`, the way `Scan` already
is. `5: Rep RP Voyager` and `5: Fire RP Voyager` are the same order.

## Consequences

**Replenishing is now something someone does for you.** A damaged ship flies home, slows down, and
asks. That is a message between two players, out of band, in the round before it matters — which is
the play-by-mail game working the way the rest of it does, and it is a reason for a faction to want
its base seat filled by somebody who is paying attention.

**It costs the lone commander.** If a faction's base has nobody at the helm, nobody in that faction
can replenish at all. Every scenario that deploys a starbase now has to give it a commander or an
NPC, where before a base was scenery that happened to restock people. The five faction war already
hands each base to one of its own players, so nothing there changes.

**The control came free.** A component that answers `expected_parameters` gets a control in both
shells without either being told it exists, so the backlog item closed itself. The map draws the
order as a line from the base to the ship it is serving, which is the same way a laser is drawn at
what it is shooting.

**The bugs went with the ship-side path.** There is no search for a replenisher, so two bases is
two bases. A refusal says which of the four conditions failed, into the base's log.

**One order per tick per replenisher is a real limit.** Three ships limping home is three ticks,
and a base carries one replenisher. Giving a later model two is the obvious lever if that turns out
to be too tight; nothing else needs to change for it.

## Alternatives rejected

**Leaving it on the ship and building the control by hand.** The order addresses the ship, so it
would have needed a bespoke button in `DesktopMap` and another in `TouchMap`, hand-written in both
and hand-kept in step — the one thing the component vocabulary exists to avoid. It also keeps all
three bugs, because a ship searching the world for a base is what causes them.

**Keeping both: the ship may ask, and the base may offer.** Two mechanisms for one action, which
doubles what a player has to learn and leaves the ship-side one carrying the enemy-base and
self-repair holes. It is worse for the command language than either alone, and a language meant to
be taught from should have one way to say a thing.

**Restricting it to the base's own faction**, which the parameter would give for nothing. It reads
as safe and it removes the only interesting decision the order has. A base that can only serve its
own is a vending machine; one that can serve anybody is a commander choosing, and being seen to
choose.

**Offering only the ships already in range.** Tempting, because the list would then be exactly what
can be served — and wrong, because orders are written ten ticks before they run. The ship you mean
to restock at tick 7 is three hundred units away when you write the order. The list is every ship
in the game, which gives away nothing: the roster is already public.

**Charging for it, or capping it per game** the way the spawner's three replacements are capped.
Possibly right, and it is a balance question this record does not settle. The old order was free
and unlimited, so this one is too until somebody plays enough rounds to say otherwise.