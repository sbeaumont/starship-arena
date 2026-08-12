# 0026. A game keeps a journal of its processing

**Status:** Accepted

## Context

A round can be processed four ways: the director presses Process, the director forces it past
missing orders, the last player says they are ready, or the hour arrives and cron runs it. Three of
those happen while nobody is watching.

The director's question the next morning is "did last night run, and what happened". Nothing
answered it. `process_due` built a summary and returned it to the CLI, which printed it and forgot
it.

Round processing is deterministic and reads no clock ([ADR 0002](0002-deterministic-rounds.md)). A
record of when things happened is nothing but clock readings.

## Decision

Each game directory holds `journal.jsonl`: one JSON object per line, appended, never rewritten. An
entry is a timestamp, an event, and whatever else that event has to say.

**The services layer stamps the time.** `arena/app` decided to process, so `arena/app` supplies
`at`; `GameDirectory.append_journal` writes the line it is handed. The engine still reads no clock.

Every entry beyond `at` and `event` is a reported dict. A screen prints the pairs without knowing
their names, so a new kind of entry, or a new detail on an old one, needs no template edit. Same
idea as a component's `status` (see [information.md](../information.md)).

`By` says who and `ProcessingTrigger` says what set a round going. They are close to one-to-one
today and they are different questions: cron is a who, a deadline is a what.

**An automatic deadline fires once per hour. A deliberate one always runs.** `process_due` skips a
game whose journal already shows a `deadline` entry in the current hour. Nothing else is guarded:
a director pressing the button twice meant it both times.

## Consequences

The console can show a game its own history, and the Processing screen can interleave every game's.

A double cron fire, a script run by hand to see what it does, and the repeated hour when daylight
saving falls back all stop at the guard. That matters because forcing a round writes empty command
files, and those are a plan: a regenerate would replay the duplicate faithfully forever.

The console had to come through `AdminService` for Process and Regenerate, which it had been
reaching past the seam to do. Two of the four known engine imports in `appfacade.py` are gone.

A failure that cannot open the game directory has nowhere to write itself. The ops log is where
that lands.

Appending under 4kB with `O_APPEND` is atomic, so two processes writing at once cannot interleave
a line, and a reader never sees half of one.

## Alternatives rejected

**Timestamping inside the engine.** It is where the detail is, and it would put a clock in the one
place that must not have one. [Round processing stays
deterministic](../architecture.md#invariants) because regenerate depends on it.

**Capturing the log records emitted during a round and attaching them to the entry.** Richer, and
it answers a question nobody asked: the director wants to know that the round ran and who was
silent, not what happened on tick 7. The ops log already keeps that.

**One journal for all games, at the data root.** A game's own history is what a screen asks for,
and a shared file makes that a filter over everything. The Processing screen interleaves them,
which is cheap at this size and is the rarer question.

**Guarding every trigger against running twice in an hour.** It would make the director's second
press do nothing and say nothing, which is worse than the duplicate it prevents.