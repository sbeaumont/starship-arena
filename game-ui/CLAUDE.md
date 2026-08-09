# The game UI

Svelte 5 and Vite, no SvelteKit. The player's map, planning and log.

1. **The whole view lives in the URL.** `?game=&player=&round=` or `?page=`, plus `?ui=` to force
   a map shell, written with `pushState`, so views are shareable and back works.
2. **Ask the API, don't infer.** If the UI needs to know whether something is allowed, the API
   says so in the data it returns. No rules duplicated in the browser.
3. **Two SVG layers.** Geometry in world coordinates, which pans and zooms; text and leader lines
   in screen pixels, which do not. Markers are sized `px * upp` so they stay constant; real
   distances like blast radii scale with the world.
4. **Render what the API sends.** Component names, event kinds and weapon inputs come from the
   server. Never hardcode a ship type, a component name or a weapon.
5. **Rebuild `dist` before committing.** It is tracked; the host has no build step.

After changing a component's props, hot reload often cannot swap it. Refresh before believing a bug.

## The map

`lib/map/` is one map played through two shells. The split is by input, not by width: a tablet in
landscape is wide and still wants fingers.

| | |
|---|---|
| `plan.js` | Orders parsed, simulated and written back. Pure, no Svelte, no DOM |
| `camera.svelte.js` | Where the map is looking. Pan, zoom, fit, grid |
| `planning.svelte.js` | One round: the picture, the orders on top of it, what is selected |
| `MapSession.svelte` | One game and player: makes the plan and the camera, and picks a shell |
| `Plot.svelte` | The two SVG layers, and every gesture that reaches them |
| `DesktopMap.svelte` | A mouse: everything at once, in three columns |
| `TouchMap.svelte` | Fingers: one mode at a time, a mode bar, a sheet |
| `Sheet.svelte`, `WeaponChips.svelte`, `WeaponBar.svelte` | The touch shell's furniture |
| `LogPanel.svelte`, `CourseTable.svelte` | Read by both shells |

Rules that bind this directory:

6. **A shell never asks which shell it is.** What one does differently arrives as a prop.
   `grabbable` - `{path, shots, ticks}` - is the whole of it: the desktop lock and the touch
   modes both reduce to it, and `Plot` reads nothing else about who is driving.
7. **Nothing derived from a plan lives in a shell.** Courses, shots, cones and labels are
   computed once, in `Planning` or in `Plot`. A shell that recomputes one is how the two drift.
8. **One gesture machine.** Pan, pinch, the wheel and both drags are in `Plot`. A shell that
   adds its own pointer handling to the map will fight it.
9. **Fingers are not cursors.** Hit targets grow with `coarse`, which only works because a mode
   has already said which of them are live. Adding a hit target means saying which mode owns it.
10. **A drag reports what it is doing.** Your hand covers the thing you are dragging, and the
    tables are not always on screen.
11. **A session is made, never derived.** `MapSession` is keyed on game and player and builds its
    `Planning` and `Camera` with plain `const`. A `$derived` that constructs one may run twice
    and hand the template a different instance from the one that was loaded, which reads as a map
    that never updates.

## Development

`npm run dev` listens on every interface, so a phone on the same network can open the map.
`./arena-link.sh <name> http://<lan-ip>:5173` issues a link that will work from it.

`?ui=touch` and `?ui=desktop` force a shell, so either can be opened on any machine.
