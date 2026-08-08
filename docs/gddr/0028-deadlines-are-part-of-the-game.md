# 0028. A round lands on the clock, and missing it costs you the round

**Status:** Accepted

## Context

A round used to run when somebody made it run: the director pressed Process, or the last player
said they were ready. Both wait on people.

A game runs for months with a handful of friends in it. One person on holiday held up everyone
else, and the only cure was the director deciding to force it, which made every deadline a
conversation.

## Decision

**A game names the hours it processes on, and at those hours the round runs.** Hours 0 to 23, any
number of them, in server time. Orders in or not.

Orders that did not arrive are an empty command file, as they have always been: the ship holds its
heading and speed for all ten ticks, fires nothing, and takes whatever the round brings. It still
generates and spends energy, and it still scans, so its faction keeps seeing what it can see. What
is new here is that a clock can be the thing that decides you sent nothing.

**The hours are open information.** Anybody can see when any game processes, logged in or not, the
same way they can see any ship's statistics ([GDDR 0012](0012-open-information.md)).

**Every screen that shows an hour says which clock it is.** The console puts the server's time in
its top bar; the player's game list shows the next deadline in the reader's own time and how long
they have. The stored hour never moves
([ADR 0027](../adr/0027-the-server-keeps-one-timezone.md)).

Readiness still works beside it. A game can also process the moment the last player says they are
done, and whichever comes first wins. **No hours at all means no deadline**, and the director runs
that game by hand.

## Consequences

**The pace of a game is the director's to set, and it is one setting.** One hour a day is a round a
day. Two is a round every twelve hours. All 24 is a round an hour, which is a different game.

**Missing a deadline costs a round, not a game.** Ten ticks of straight-line flight is rarely fatal
on its own. It is also the most predictable thing on the map, so what it really costs depends on
where you left the ship: holding course into a minefield, or across an enemy's arc, is how a missed
round becomes a lost ship.

**A player has to plan around a time of day.** That is new, and it is the point: the deadline is
information everybody has, so leaving your orders to the last hour is a choice with a cost rather
than an accident.

**Waiting on the slowest player stops being everybody's problem.** It becomes that player's
problem, which is where it belongs.

**A missed deadline is in the record forever.** The empty command file is a plan
([docs/data.md](../data.md)), so a regenerate replays the round exactly as it happened, silence and
all.

**The deadline fires once an hour, whatever cron does.** A double run, or somebody running the
script by hand, cannot take two rounds off a game. A director forcing it twice still can, because
they meant it ([ADR 0026](../adr/0026-a-game-keeps-a-journal.md)).

## Alternatives rejected

**Waiting for everyone, always.** This is what readiness alone does, and it is still available
beside the clock. As the only mechanism it means one person away for a week costs five other people
a week, and the director spends the game asking after orders.