# 0016. The whole view lives in the URL

**Status:** Accepted

## Context

The game UI shows a player's map for a given game and round, a replay of a game, and a few
reference pages. The console wants to link a director straight to a player's map. Players want to
send each other a view, and a link somebody is sent should read as the thing it opens.

## Decision

The view is the path.

| | |
|---|---|
| `/` | home |
| `/ships`, `/lore`, `/register`, `/solo` | the reference pages |
| `/valhalla` | the games that are over |
| `/valhalla/xke`, `/valhalla/xke/Two` | one of them, whole or from one side |
| `/replay/xke`, `/replay/xke/Two` | a game still being played, the same two ways |
| `/games/xke/Menno`, `/games/xke/Menno/2` | a commander's map, at their latest round or at one |

Written with `pushState`, read back on `popstate`. There is no route table and no state that only
exists in memory: `readUrl` and `urlFor` in `App.svelte` are the whole of it, and they are each
other's inverse.

Two things stay out of the path.

**The tick a replay is parked on is the fragment**, `#120`. It is a place inside the page, and the
playhead rewrites it every step, so it belongs where a fragment belongs and never reaches the
server.

**Which map shell to use is `?ui=touch`.** A preference rather than a view, so it rides along
every navigation instead of naming one.

Identity is deliberately neither. A `?login=` token is traded for a cookie and then stripped with
`replaceState`.

## Consequences

Back and forward work without any work.

Anything the server has no file for is the app, since a path is a view rather than a file
(`arena/serve.py`). A path whose last segment has a dot in it is a missing file and still answers
404, so a broken build fails loudly instead of serving the app in an asset's place.

Assets are referenced from the root rather than relatively. `/valhalla/xke` would resolve a
relative asset against `/valhalla/` and find nothing.

The console links to `{game_ui_url}/games/xke/Menno` and lands exactly where it means to.

Because identity is a cookie rather than a URL, sharing a view is never sharing an account. That
distinction only holds if nothing ever puts the token back in the URL.

Reference pages are checked before the login gate, so a prospective player can read the ships and
the lore without a link.

## Alternatives rejected

**Every piece of view state as a query parameter**, `?game=xke&player=Menno&round=2` and
`?page=ships`, which is what this was for its first two years. It needs nothing of the server, and
that is its whole case. A link is then a sentence of machinery rather than a name, and the one
people most wanted to send, a game in Valhalla at the moment it turned, read as
`?page=valhalla&game=xke&faction=Two&tick=120`.

**Component state only.** Nothing to share, no back button, and the console's deep links become
impossible.

**A client-side router.** A dependency and a route table for what two functions do.

**Keeping the login token in the URL.** Simplest to implement, and it makes a shared view a shared
identity. The whole point of the URL carrying state is that URLs get passed around.