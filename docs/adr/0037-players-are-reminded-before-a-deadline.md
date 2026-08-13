# 0037. Players are reminded before a deadline

**Status:** Accepted

## Context

A game processes on the hours its settings name, and a deadline processes whether the orders are in
or not: whoever sent nothing gets an empty command file and plays the round standing still. The
game already says a round is *out*
([ADR 0029](0029-announcements-leave-through-channels.md)). Nothing says one is *due*.

Discord offers three ways to reach a person and only one of them survives contact with a player's
settings. A bot can open a DM, but only if it shares a server with them and they have not turned
off messages from server members, and it finds out which by being refused. An ephemeral message,
the in-channel whisper, exists only as a reply to a slash command and Discord has refused to allow
it any other way. A mention in a channel everyone is already in cannot be blocked by anything, and
one message carries every name it needs to.

## Decision

**Reminders are per player, not per ship.** A commander with a fleet of three owes orders once.
`_fleets_in` groups a game's ships by who commands them, and both the standing and the reminder
read it, so there is one definition of what a person owes.

**A player says when, two ways, and picks either or both.** `remind_hours_before` is a lead time on
whatever the game's next deadline is. `remind_daily_hour` with `timezone` is an hour of their own
day, which is the one people can actually plan around: a working rhythm is 24 hours long, and "tell
me at eight" is a thing somebody can decide once. Both ride on `discord_id`, all of it in
`players.jsonl`, and everything absent is what everyone starts as. It is opt-in because the id has
to come from somewhere, and half an opt-in is a poke nobody can turn off.

**Whole hours, because the pass that sends these runs on the hour.** Offering minutes would offer a
precision nothing downstream keeps: a reminder set for 08:45 goes out at whatever o'clock the cron
next fires. So the setting is an hour, spelled the way `process_hours` already spells one, and the
screen offers a list of 24 rather than a clock widget with a minute field nobody can act on.

**A player's chosen hour is the one thing kept on their clock, and it is stored as a wall-clock
time plus a zone name.** [ADR 0027](0027-the-server-keeps-one-timezone.md) turned down *storing a
converted time*, because daylight saving would move it twice a year with nobody touching anything.
The pair is what that argument asks for rather than against: `08:30` and `Europe/Amsterdam` mean
the same morning in July and December, and the offset is worked out from the zone's own rules on
the day. Nothing converted is stored, a game's `process_hours` are still server hours, and
`their_hour_today` in `clock.py` is the only place that reads a player's zone.

**The poke is a mention in the announcement channel**, through the announcer that is already there,
gated by the same per-game `announce` setting. No bot, no token, no permissions, no DM that a
privacy setting can silently swallow.

**`remind_due` is its own cron action on its own schedule.** Running it at half past reaches people
in time for the hour a game processes on. `arena-cron.sh` takes the action and defaults to
`process_due`, so the two share one copy of the virtualenv hunt.

**The journal records who was reached and by which of the two, and that is what stops a second run
repeating it.** A `reminded` entry naming the players and its `trigger`. A `deadline` one counts
for the round it names; a `daily` one counts for the day it was written. Nothing measures elapsed
time and nothing is held between runs, so how often the cron fires is a crontab decision alone.

**Recording the names rather than the fact** is what lets two settings coexist. Someone wanting a
day's warning and someone wanting an hour's are two separate reminders for the same round, and an
entry that said only "this game has been reminded" would swallow the second. The `trigger` does the
same job for one person who asked for both: two reminders, and neither reads as the other.

**A reminder no channel took is not recorded**, so the next pass tries those people again. The
announcer returns what it reached for that reason; a caller with nothing riding on delivery ignores
it, as the round announcement does.

## Consequences

Both settings mean *no earlier than*, and the cron cadence decides how close they land. An hourly
pass with a one-hour lead can fire at thirty minutes out, and a chosen `08:00` goes out on the
first pass at or after it. Running the pass more often tightens both without a line of code
changing.

The mention is `<@id>`, markup only Discord understands, in a sentence composed in the services
layer. That is where the sentence has to be composed, and the announcement already carries
`**bold**` for the same reason. The day a second channel exists the announcer will have to hand a
channel something richer than a string, and the recipients go in it then, not now.

Nothing sets these fields yet. The director edits `players.jsonl`, and the profile page that lets a
player set their own is the next piece rather than part of this one. The browser knows the zone to
put in it: `Intl.DateTimeFormat().resolvedOptions().timeZone` is the IANA name, so choosing it is
not a question anyone has to be asked.

Someone who commands a ship but has no row in `players.jsonl` is never poked. They cannot be: the
id is the address.

A channel that fails is logged and dropped, and the entry is written anyway, so a webhook that is
down costs those players that round's reminder. Same tolerance
[ADR 0029](0029-announcements-leave-through-channels.md) already sets, and the deadline still
processes: a missed poke is a missed poke, not a missed round.

The journal is now read back to decide something, which it was already: `_deadline_already_fired`
does the same. Losing it still loses no game. The cost is a duplicate poke, and a round processed
twice in an hour was always the worse of the two.

## Alternatives rejected

**A DM to each player.** It fails silently for anyone whose privacy settings refuse a bot, and it
finds out only by being refused, so the reliable case degrades into no reminder rather than a
noisier one. Discord's own documentation says not to use that endpoint to message everyone in a
server. Worth adding as a per-player upgrade, feeding the same path, once the channel poke is
carrying the game.

**An ephemeral whisper in the channel.** Discord only issues one against an interaction token, and
has said it will not allow uninvoked ones because a message no moderator can see is too useful to
an abuser.

**A channel or a webhook per game.** It buys per-game privacy, and one webhook plus a mention buys
the same reminder. [ADR 0029](0029-announcements-leave-through-channels.md) turned this down for
announcements and nothing here changes the arithmetic.

**Staying stateless by telling the command its own window**, `remind_due --window 30`, and firing
on the reminder moment landing inside it. Then the crontab interval is a fact in two places with
nothing checking they agree, and moving the cron line silently doubles or drops reminders.

**A player's zone as a UTC offset rather than a name.** `+02:00` is right for half the year, and
the half it is wrong for is the half nobody is thinking about when they set it. A name carries the
rules; an offset carries one day's answer to them.

**One message per player, gathering every game they owe orders in.** It reads better for the daily
reminder, and it makes that reminder a different shape from the deadline one: a pass over players
rather than over games, a sentence naming several games, and a record with nowhere to live because
the journal is per game. Worth revisiting when somebody is in enough games at once to notice.

**A separate file recording who was poked.** The journal is what the server did to a game, and this
is that. A second record would need its own lifecycle beside a game that already has one.