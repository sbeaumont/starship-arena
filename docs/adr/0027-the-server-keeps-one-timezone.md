# 0027. The server keeps one timezone, and shifting is a UI concern

**Status:** Accepted

## Context

A game names the hours it processes on, and cron fires hourly to make those hours happen. So
`process_hours` has to mean the same thing the crontab means.

Three clocks are in play and none of them have to agree. The host runs UTC on PythonAnywhere. The
director thinks in Amsterdam. Players are wherever they are.

## Decision

The server keeps the timezone of the host it runs on. There is no setting for it.

Every hour in `settings.jsonl` and every timestamp the server writes is in that zone, and every
comparison it makes is against that zone.

Shifting to a reader's clock happens in the interface and nowhere else. A converted time is never
stored, never submitted, and never travels back down.

`arena/app/clock.py` is the only place that reads real time. The engine reads no clock at all
([ADR 0002](0002-deterministic-rounds.md)).

## Consequences

One clock. The cron entry, the log timestamps, the host's own files and the game all agree about
what hour it is, and no question ever needs qualifying with which clock it is in.

On PythonAnywhere that clock is UTC, so a game's hours are UTC hours. Every screen that shows them
says so, and shows the server's current time beside them.

An interface may show a reader their own time next to the server's, because that is presentation.
The moment a converted hour could be saved, the setting stops meaning what the crontab means.

Daylight saving bites only where the host has it. A UTC host has none, so the repeated hour and
the skipped one are a laptop's problem rather than the deployment's.

The host's zone has no name the standard library can produce, only the abbreviation it reports, so
a label reads `CEST` rather than `Europe/Amsterdam`.

## Alternatives rejected

**A `SERVER_TIMEZONE` setting, so the games could run on Amsterdam hours from a UTC host.** Built,
then taken out. An application keeping a different clock from the machine under it means the cron
log, the file timestamps and the game disagree about what hour it is, and every answer has to be
qualified with which of them it came from. The hours being UTC is a thing to read off a screen
once; two clocks is a thing to reason about forever.

**Converting to each reader's zone on the way in, and storing the result.** Twice a year daylight
saving would move every deadline by an hour with nobody having touched anything, and the stored
number would stop agreeing with the crontab that acts on it.

**Reading the host's zone name from `/etc/localtime`.** It is a symlink into `zoneinfo/` on macOS
and most Linux, and parsing it gives `Europe/Amsterdam`. On PythonAnywhere it is a plain file with
no name in it, so the one host that matters is the one it cannot answer for. The abbreviation is
enough for a label, and `datetime.astimezone()` already reads the host's rules for whatever date
it is asked about, December as CET and July as CEST.