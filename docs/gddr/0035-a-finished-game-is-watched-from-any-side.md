# 0035. A finished game is watched from any side

**Status:** Accepted

## Context

Fog of war is the game ([GDDR 0013](0013-fog-of-war-from-scans.md)). A commander sees their own
ships and whatever their side scanned, and the director alone gets every side at once, because
that is more than anybody in the game saw.

Those rules protect a game that is still being played. A game that is over has nobody left to keep
anything from, and it has the opposite problem: nothing to show. A war fought over six weeks ends
up as a directory of pickles that only its own players ever looked at, one side at a time.

## Decision

A game that has been exported to Valhalla is public, and it is watched the way it was fought.

Anybody, signed in or not, may open one and pick a side. Faction Two's war shows Two's ships as
they were and everything else only where Two's commanders scanned it, dashed and course-less,
exactly as it looked to them at the time. Picking every side at once shows all of it: every ship,
every course, nothing dashed.

The export keeps the scans for this. Per object, per tick, what it saw and where that was — the
same record a live game builds its fog from, so the two views of a game are the same view built
twice ([ADR 0034](../adr/0034-a-finished-game-is-exported-to-a-schema-of-its-own.md)).

Nothing else about a finished game is narrowed. There is no login to check, so there is nothing to
check it against.

## Consequences

The museum is the front door. Somebody who has never played can watch a whole war before deciding
whether to ask for a name, which no page could offer while every replay needed a login.

A commander can finally see what the other side was doing while they were guessing, which is most
of the pleasure of a game being over. Watching their own side back is the same picture they
planned against, not a god view retrofitted with their name on it.

Exporting is what makes a game public, and it is a button. A game the director exports while it is
still being played is a game whose fog is now readable by both sides from any browser. That is the
one thing to know before pressing it: the export is a copy, and the copy has no secrets.

Every side is offered, including sides with nobody left alive. A war of three where one was wiped
out in round two is watchable from inside that faction, which is its own kind of story.

## Alternatives rejected

**Every side at once, and nothing else.** What the format was first written for: a finished game
is shown to everybody, so the only view a museum needs is the one that sees all of it. It is
cheaper, it needs no scans in the file, and it throws away the thing a replay is for. Watching a
salvo come out of empty space towards ships that have not seen it yet is the game; watching two
sets of ships that both knew everything is a diagram.

**The director's login, extended to whoever asks.** Reuses the existing check by widening who
passes it. It reads as an oversight rather than a decision, and the next person to tighten
permissions takes it out. Where a game is kept is what makes it public, and a directory cannot be
forgotten by a caller.

**Fog rebuilt in the browser from the whole document.** One request, and the viewer switches sides
instantly. It also means the page holds every side's picture while claiming to show one, so the
narrowing is a filter over a payload that has the answers in it. Harmless here, and it is the
habit that leaks a live game.