# The game UI

Svelte 5 and Vite, no SvelteKit. The player's map, planning and log.

1. **The whole view lives in the URL, as a path.** `/games/xke/Menno/2`, `/valhalla/xke/Two`,
   `/ships`. The tick a replay is parked on is the fragment and `?ui=` forces a map shell; nothing
   else rides outside the path. Written with `pushState`, so views are shareable and back works.
   [ADR 0016](../docs/adr/0016-the-view-lives-in-the-url.md)
2. **Ask the API, don't infer.** If the UI needs to know whether something is allowed, the API
   says so in the data it returns. No rules duplicated in the browser.
3. **Two SVG layers.** Geometry in world coordinates, which pans and zooms; text and leader lines
   in screen pixels, which do not. Markers are sized `px * upp` so they stay constant; real
   distances like blast radii scale with the world.
4. **Render what the API sends.** Component names, event kinds and weapon inputs come from the
   server. Never hardcode a ship type, a component name or a weapon.
5. **Rebuild `dist` before committing.** It is tracked; the host has no build step.
6. **Two shells, one feature.** Anything the map gains lands in `DesktopMap` and `TouchMap` both,
   layer toggles included, and anything a finger reaches for gets a finger-sized target. Diverging
   is allowed and is a decision to write down; it is never an omission. The pages outside the map
   are one responsive implementation rather than two, and have to hold at phone width.

**Colour answers one question**, and the questions are in
[GDDR 0033](../docs/gddr/0033-colour-answers-one-question.md). A new mark picks its question before
it picks a colour, and one that answers two is two marks. Values live in `app.css`;
`test/docs/test_colours.py` fails any style block that spells one out instead of naming it.

After changing a component's props, hot reload often cannot swap it. Refresh before believing a bug.

## The map

`lib/map/` is one map played through two shells. The split is by input, not by width: a tablet in
landscape is wide and still wants fingers.

| | |
|---|---|
| `plan.js` | Orders parsed, simulated and written back. Pure, no Svelte, no DOM |
| `markers.js` | The shapes an object in space is drawn as. Pure, and shared with the replay |
| `camera.svelte.js` | Where the map is looking. Pan, zoom, fit, grid |
| `planning.svelte.js` | One round: the picture, the orders on top of it, what is selected |
| `MapSession.svelte` | One game and player: makes the plan and the camera, and picks a shell |
| `Plot.svelte` | The two SVG layers, and every gesture that reaches them |
| `DesktopMap.svelte` | A mouse: everything at once, in three columns |
| `TouchMap.svelte` | Fingers: one mode at a time, a mode bar, a sheet |
| `Sheet.svelte`, `WeaponChips.svelte`, `WeaponBar.svelte` | The touch shell's furniture |
| `LogPanel.svelte`, `CourseTable.svelte` | Read by both shells |

Rules that bind this directory:

7. **A shell never asks which shell it is.** What one does differently arrives as a prop.
   `grabbable` - `{path, shots, ticks}` - is the whole of it: the desktop lock and the touch
   modes both reduce to it, and `Plot` reads nothing else about who is driving.
8. **Nothing derived from a plan lives in a shell.** Courses, shots, cones and labels are
   computed once, in `Planning` or in `Plot`. A shell that recomputes one is how the two drift.
9. **One gesture machine.** Pan, pinch, the wheel and both drags are in `Plot`. A shell that
   adds its own pointer handling to the map will fight it.
10. **Fingers are not cursors.** Hit targets grow with `coarse`, which only works because a mode
    has already said which of them are live. Adding a hit target means saying which mode owns it.
11. **A drag reports what it is doing.** Your hand covers the thing you are dragging, and the
    tables are not always on screen.
12. **A session is made, never derived.** `MapSession` is keyed on game and player and builds its
    `Planning` and `Camera` with plain `const`. A `$derived` that constructs one may run twice
    and hand the template a different instance from the one that was loaded, which reads as a map
    that never updates.

## The replay

`lib/replay/` plays a whole game back, a tick at a time. Whose side it is decides what the API will
even send: a commander gets their own side and the sightings its ships took, the director gets every
side at once. The side is in the URL and the page is keyed on it, so switching is a fresh playhead
rather than a filter over something already downloaded.

**Two sources, one payload.** A game being played comes off its saved worlds; a game that is over
comes out of Valhalla, `museum` in the props and one different path in `Playhead`. Both arrive as
the same `GameReplay`, and nothing here knows the museum's format exists - a reader per version of
it is kept in Python, forever, and one in JavaScript would be that obligation twice
([ADR 0034](../docs/adr/0034-a-finished-game-is-exported-to-a-schema-of-its-own.md)). A finished
game is watched from any side by anybody, which is why the side switcher is not the director's
there ([GDDR 0035](../docs/gddr/0035-a-finished-game-is-watched-from-any-side.md)).

**View as Player has to reach the API here.** A director with it on asks for `as_player`, so the
narrowing happens before anything is sent rather than in the browser. Anywhere else the toggle only
changes what a page offers; a replay is data, and a filter over a payload that holds every side is
not a player's view of it.

| | |
|---|---|
| `playhead.svelte.js` | Which tick, how much trail, whether it is running. Turns an abs tick into a round and a tick |
| `Replay.svelte` | The two SVG layers, the pointers, and the log of the tick being watched |
| `Transport.svelte` | Step, rewind, run, scrub, and how long the trail is |

It shares the map's `camera.svelte.js` and `markers.js`, so a starbase is drawn one way. **The
pointer handling is its own**, and that is a decision rather than an omission: nothing in a replay
is draggable, so there is no mode to ask about and none of `Plot`'s gesture machine applies. Labels
are not pushed apart the way the map's are, so names overlap in a tight formation.

One responsive implementation rather than two shells, like the other pages: the log sits beside the
picture and drops under it when there is no room.

## The icon

`public/favicon.svg` is the source. The three PNGs beside it are rendered from it, so a new
drawing means rendering them again or the home screen keeps the old one:

```bash
cd game-ui/public
for s in 180 192 512; do
    inkscape --export-type=png --export-width=$s --export-height=$s \
             --export-filename="icon-$s.png" favicon.svg
done
```

What a replacement has to hold to, whoever draws it:

- **Full bleed.** iOS puts its own background behind a transparent icon, so the artwork owns
  every pixel of the square.
- **Inside the safe circle.** Android may crop a maskable icon to a centred circle of 80%
  diameter. Anything outside that is decoration, not subject.
- **Legible at 32px.** One subject, and detail that is thin enough to disappear rather than
  turn to noise when the icon is small.
- **A PNG for iOS.** `apple-touch-icon` does not read SVG, which is what `icon-180.png` is for.

## Development

`npm run dev` listens on every interface, so a phone on the same network can open the map.
`./arena-link.sh <name> http://<lan-ip>:5173` issues a link that will work from it.

`?ui=touch` and `?ui=desktop` force a shell, so either can be opened on any machine.
