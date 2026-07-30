# 0014. Logins are a magic link per person

**Status:** Accepted

## Context

The game had no authentication. The selector listed every player and relied on honour, with a note
asking people to look only at their own ships.

The players are a handful of friends. Rounds take a week. Nobody wants an account, and nobody wants
to run a password reset.

A person plays across games and seasons, and their name already appears in every `ships.txt` they
command a ship in.

## Decision

One token per **person**, not per game. The name is the identity everywhere.

A token arrives in a link, is traded once for a long-lived cookie, and the link is then forgotten.
The URL is cleaned with `replaceState` so a shared view never carries an identity.

Tokens live in `players.txt` in plain text. Issuing again replaces the old one, which is also how a
leaked link is dealt with.

The director is a role in the same file. The console lets in nobody else.

Someone unknown can register a name, provided no game already uses it. A name that commands ships
belongs to whoever the director gave them to, and they get a link from the director.

## Consequences

No passwords, no reset flow, no user management. Issuing a link is one command or one button.

A single link works across every game a person plays, and next season too.

Access follows the game data. A player's games are the ones whose `ships.txt` names them, so there
is no separate grant to maintain.

A token in plain text is readable by anyone with the data root, which on this host means the owner.
That's the trade for being able to re-send a link, and for hand-editing your way back in.

Losing every director token locks the console. The CLI is the way back, which is why issuing links
lives there as well as in the UI.

The first link has to come from a shell. There's no bootstrap page, deliberately: a page that
grants director rights to whoever finds it first is worse than a chicken-and-egg problem.

## Alternatives rejected

**Accounts with passwords.** The abandoned `user.py` in this repo did that, storing them in plain
text. It needs registration, reset and hashing, all to identify eight people who already know each
other.

**A token per (game, player).** Simpler to reason about, and it means a new link every season and a
player holding several at once.

**Hashed tokens.** Correct for a real service. Here it removes the ability to re-send a link, and
the threat model is friends behind a site password.

**Self-registration of any free name.** Rejected because a name that commands ships would be
claimable by whoever asked first, which hands over a fleet.
