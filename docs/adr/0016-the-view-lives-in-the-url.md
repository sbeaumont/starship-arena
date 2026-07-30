# 0016. The whole view lives in the URL

**Status:** Accepted

## Context

The game UI shows a player's map for a given game and round, plus a few reference pages. The
console wants to link a director straight to a player's map. Players want to send each other a
view.

## Decision

Every piece of view state is a query parameter: `?game=xke&player=Menno&round=2`, or `?page=ships`.

Written with `pushState`, read back on `popstate`. There's no separate route table and no state
that only exists in memory.

The one thing deliberately kept out is identity. A `?login=` token is traded for a cookie and then
stripped from the URL with `replaceState`.

## Consequences

Back and forward work without any work.

The console links to `{game_ui_url}/?game=…&player=…` and lands exactly where it means to.

Any view can be pasted to someone, and they see the same thing if they're allowed to.

Because identity is a cookie rather than a URL, sharing a view is never sharing an account. That
distinction only holds if nothing ever puts the token back in the URL.

Reference pages are checked before the login gate, so a prospective player can read the ships and
the lore without a link.

## Alternatives rejected

**Component state only.** Nothing to share, no back button, and the console's deep links become
impossible.

**A client-side router.** A dependency and a route table for what is four query parameters.

**Keeping the login token in the URL.** Simplest to implement, and it makes a shared view a shared
identity. The whole point of the URL carrying state is that URLs get passed around.
