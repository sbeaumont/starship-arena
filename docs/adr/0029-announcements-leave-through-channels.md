# 0029. Announcements leave the game through channels

**Status:** Accepted

## Context

A round can be processed four ways, and three of them happen while nobody is watching
([ADR 0026](0026-a-game-keeps-a-journal.md)). The players find out by opening the map and
looking. A game that processes at 07:00 is a game everyone has to remember to check.

The players already talk to each other on Discord, and a Discord server hands out a webhook URL
that takes an HTTP POST and prints the text in a channel. That is the whole protocol.

Two constraints decide where this can live. The engine may not reach outward, and
`regenerate_game` drives `process_current_round` in a loop to replay a game, so anything hung off
that call fires again for every round it replays.

## Decision

`arena/announce.py` sits beside the layers, where `log.py` and `cfg.py` sit. It imports `cfg` and
nothing else of ours.

A **channel** is somewhere a message can go. It says whether it has an address, and it takes text.
`DiscordWebhook` is the only one today. An **announcer** says the same thing on every channel that
has an address.

**Nothing in there knows what a round is.** The services layer composes the sentence, because that
is where the game's vocabulary is, and the channel only knows how to deliver a string.

**The announcement is written beside the journal line, at each of the three places that write one.**
A journal entry is a record and an announcement is a message. Regenerating writes the first and
must not send the second, and folding them together would make that a test on the event name.

**One webhook for the whole installation**, read from the environment or `secret.py`. A game says
*whether* it announces, not *where to*: `settings.jsonl` gains `announce`, and a game that has
never been told announces. The director who wants quiet is the rare one.

**A channel that fails is logged and dropped.** By the time this runs the round is processed and
saved, and turning a dead webhook into a failed round would be worse than the silence.

## Consequences

No new dependency. `urllib.request` posts JSON perfectly well, and the alternative was `requests`
for one call.

The POST happens inside whatever request or cron run processed the round. Discord answers in well
under a second. A thread would be the way to stop paying for it, and [nothing creates a thread at
import](../architecture.md#invariants) exists to keep threads out of a preforked host.

A host that cannot reach Discord gets a warning in the ops log and a game that ran fine. Silence
is the only symptom, so `python -m arena.cli.main announce` exists to ask the question directly.

Email is a second channel and a second entry in `cfg`. It will want a subject line and a list of
addresses, which is a channel's own business, but the day it arrives the announcer may have to
hand a channel something richer than a string.

A failed announcement leaves no mark in the journal. The ops log has it, and the journal is about
what happened to the game.

## Alternatives rejected

**Announcing from inside `Game.process_current_round`.** It is the one place every route to a
processed round passes through, which is exactly why it cannot be there: regenerate passes through
it too, once per replayed round. And it would put an HTTP call in the engine.

**Folding the announcement into `_append_journal`.** Every entry would announce, including
`regenerated` and `failed`, and the guard against that would be a comparison on the event string
in the one method that was written to not care what the event is.

**A webhook URL per game, in `settings.jsonl`.** Worth having when there are several Discord
servers. There is one, and a game's settings file is not a place to keep a secret.

**Posting on a background thread.** [Nothing creates a thread at
import](../architecture.md#invariants).

**Sending each player their own message.** That is email, and email is a channel with a recipient
list, retries and an unsubscribe. Its own decision, on its own day.