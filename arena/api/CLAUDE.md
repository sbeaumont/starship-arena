# The JSON API

Translation between HTTP and `arena/app`. No game logic lives here.

1. **Call the services layer, never the engine.**
2. **Identity comes from the cookie, never from the path.** A route may take a player name, and it
   still checks that the caller is that player or the director.
3. **Refuse with the right code.** 401 when nobody is logged in, 403 when it isn't theirs.
4. **Open on purpose:** `/games`, `/{game}/overview` and `/ship-types` need no login. The
   scoreboard and the ship stats are public; positions and orders are not.
