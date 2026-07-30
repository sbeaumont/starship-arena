# The game UI

Svelte 5 and Vite, no SvelteKit. The player's map, planning and log.

1. **The whole view lives in the URL.** `?game=&player=&round=` or `?page=`, written with
   `pushState`, so views are shareable and back works.
2. **Ask the API, don't infer.** If the UI needs to know whether something is allowed, the API
   says so in the data it returns. No rules duplicated in the browser.
3. **Two SVG layers.** Geometry in world coordinates, which pans and zooms; text and leader lines
   in screen pixels, which do not. Markers are sized `px * upp` so they stay constant; real
   distances like blast radii scale with the world.
4. **Render what the API sends.** Component names, event kinds and weapon inputs come from the
   server. Never hardcode a ship type, a component name or a weapon.
5. **Rebuild `dist` before committing.** It is tracked; the host has no build step.

After changing a component's props, hot reload often cannot swap it. Refresh before believing a bug.
