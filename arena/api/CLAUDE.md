# The JSON API

Translation between HTTP and `arena/app`. No game logic lives here.

1. **Call the services layer, never the engine.**
2. **Identity comes from the cookie, never from the path.** A route may take a player name, and it
   still checks that the caller is that player or the director.
3. **Refuse with the right code.** 401 when nobody is logged in, 403 when it isn't theirs.
4. **Open on purpose:** `/games`, `/{game}/overview`, `/ship-types`, `/manual` and `/time` need no
   login. The scoreboard, the ship stats, the rules and when a game processes are public;
   positions and orders are not.
