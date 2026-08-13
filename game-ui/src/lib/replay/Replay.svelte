<script>
  import { Camera } from "../map/camera.svelte.js";
  import { burst, markerFor } from "../map/markers.js";
  import { NAMED, clamp, w2v } from "../map/plan.js";
  import { Playhead } from "./playhead.svelte.js";
  import Transport from "./Transport.svelte";

  // A game played back, one tick at a time. Never anybody's tactical picture: no orders, nothing
  // to drag. Whose side it is decides what the API sends, and a game that is over sends any of it
  // to anybody.
  //
  // The shapes come from the map's own `markers.js` and the camera is the map's camera. The
  // pointer handling is this view's own, and simpler on purpose: nothing here is draggable, so
  // there is no mode machine to share.
  let { game, faction = null, tick = null, directing = false, museum = false,
        onTick, onFaction, onLeave } = $props();

  // The initial value is the only value: App keys this on the game and the side being watched, so
  // either of those is another instance rather than a change to this one.
  // svelte-ignore state_referenced_locally
  const ph = new Playhead(game, { faction, from: tick, asPlayer: !directing, museum });
  const camera = new Camera();

  $effect(() => { ph.load(); });

  // Framed once, over everywhere the game went, which is what you want to see first.
  let framed = $state(false);
  $effect(() => {
    if (framed || !ph.data || !camera.boxW || !camera.boxH) return;
    camera.fitTo(ph.data.objects.flatMap((o) => o.path.map((r) => w2v(r.x, r.y))));
    framed = true;
  });

  const fit = () => camera.fitTo(ph.shown.map((o) => w2v(o.now.x, o.now.y)));

  $effect(() => {
    if (!ph.playing) return;
    const id = setInterval(() => ph.advance(), 1000 / ph.perSecond);
    return () => clearInterval(id);
  });

  // Shareable at any tick, replaced rather than pushed: playing a whole game would otherwise
  // leave 400 entries between you and the back button.
  $effect(() => { if (ph.data) onTick(ph.at); });

  const upp = $derived(camera.upp);
  const vb = $derived(camera.vb);

  // A tick of energy and movement per object is most of what a game records, and it is the kind a
  // reader has to ask for.
  let everyMessage = $state(false);
  const lines = $derived(everyMessage ? ph.log : ph.log.filter((e) => e.kind !== "internal"));

  // Narrow, the log is a drawer rather than a band under the map: it would take a third of a
  // phone whether or not anything happened on the tick. Wide, it is always beside the picture and
  // this does nothing.
  let logOpen = $state(false);

  // The map's KILL_RADIUS, so the moment something was killed reads the same size in both.
  const KILL_RADIUS = 20;

  const TAILS = [1, 3, 10];
  const SPEEDS = [1, 3, 6];

  const trailOf = (o) =>
    o.trail.map((r) => { const v = w2v(r.x, r.y); return `${v.vx},${v.vy}`; }).join(" ");

  // A sighting has no course of its own. Two of them infer one, which is how the map reads a
  // contact's track; a single one is drawn as a blip with no direction to it.
  function courseOf(o) {
    if (o.now.heading !== null) return o.now.heading;
    if (o.trail.length < 2) return null;
    const a = o.trail[o.trail.length - 2], b = o.now;
    if (a.x === b.x && a.y === b.y) return null;
    return (Math.atan2(b.x - a.x, b.y - a.y) * 180) / Math.PI;
  }

  // ===== Pointers: pan with one, pinch with two, and the wheel zooms =====

  let svgEl;
  const pointers = new Map();
  let last = null, pinch = null;

  function spread() {
    const [a, b] = [...pointers.values()];
    const box = svgEl.getBoundingClientRect();
    return { dist: Math.hypot(a.x - b.x, a.y - b.y),
             px: (a.x + b.x) / 2 - box.left, py: (a.y + b.y) / 2 - box.top };
  }

  function down(e) {
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    svgEl.setPointerCapture(e.pointerId);
    if (pointers.size === 2) pinch = spread();
    else last = { x: e.clientX, y: e.clientY };
  }

  function move(e) {
    const held = pointers.get(e.pointerId);
    if (!held) return;
    held.x = e.clientX;
    held.y = e.clientY;
    if (pointers.size >= 2) {
      const now = spread();
      if (pinch && now.dist > 0 && pinch.dist > 0) {
        camera.zoomAt(pinch.px, pinch.py, pinch.dist / now.dist);
        camera.panByPixels(now.px - pinch.px, now.py - pinch.py);
      }
      pinch = now;
      return;
    }
    camera.panByPixels(e.clientX - last.x, e.clientY - last.y);
    last = { x: e.clientX, y: e.clientY };
  }

  function up(e) {
    pointers.delete(e.pointerId);
    pinch = null;
    // A finger lifted off a pinch leaves the other one panning from where it is.
    if (pointers.size === 1) last = { ...[...pointers.values()][0] };
    try { svgEl.releasePointerCapture(e.pointerId); } catch (_) { /* already gone */ }
  }

  const WHEEL_ZOOM = 1.06, NOTCH_PX = 100;

  function wheel(e) {
    e.preventDefault();
    const px = clamp(e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY, -NOTCH_PX, NOTCH_PX);
    const box = svgEl.getBoundingClientRect();
    camera.zoomAt(e.clientX - box.left, e.clientY - box.top,
                  Math.exp((px * Math.log(WHEEL_ZOOM)) / NOTCH_PX));
  }

  // Arrows step and space plays, which is what a transport reads as on a machine with a keyboard.
  function onKey(e) {
    const tag = e.target?.tagName;
    if (tag === "INPUT" || tag === "SELECT") return;
    if (e.key === "ArrowRight") ph.step(1);
    else if (e.key === "ArrowLeft") ph.step(-1);
    else if (e.key === " ") ph.toggle();
    else if (e.key === "Home") ph.toStart();
    else if (e.key === "End") ph.toEnd();
    else return;
    e.preventDefault();
  }

  $effect(() => {
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  });
</script>

<div class="replay">
  <header>
    <button type="button" class="back" onclick={onLeave} title="Back to the games">←</button>
    <h1>{game}</h1>
    {#if ph.data}
      {#if directing || museum}
        <!-- Every side at once is more than anybody saw, so while a game is on it is the
             director's alone. Once it is over there is nobody left to keep it from. The picker
             says whose side this is, so nothing beside it repeats that. -->
        <span class="spacer"></span>
        <select value={ph.data.faction ?? ""} onchange={(e) => onFaction(e.currentTarget.value || null)}>
          <option value="">Every side</option>
          {#each ph.sides as f (f)}<option value={f}>Faction {f}</option>{/each}
        </select>
      {:else}
        <!-- No picker: a commander watches their own side and nothing says which one it was. -->
        <span class="sub">faction {ph.data.faction}, and what it saw</span>
        <span class="spacer"></span>
      {/if}
      <!-- Whole, on a line of its own: a legend that wraps puts two of the sides under the
           other three and reads as two different things. -->
      <span class="legend">
        {#each ph.sides as f (f)}
          <span class="side"><i style="background: {ph.hue[f]}"></i>{f}</span>
        {/each}
      </span>
    {/if}
  </header>

  <div class="body">
    <div class="plot" bind:clientWidth={camera.boxW} bind:clientHeight={camera.boxH}>
      {#if ph.loading}
        <p class="overlay">Reading the whole of {game}…</p>
      {:else if ph.error}
        <p class="overlay err">{ph.error}</p>
      {/if}

      <!-- Geometry, in world coordinates. Pans and zooms. -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <svg bind:this={svgEl} class="world"
           viewBox={`${vb.x} ${vb.y} ${vb.w} ${vb.h}`} preserveAspectRatio="none"
           role="img" aria-label="The game played back. Drag to pan, pinch or scroll to zoom."
           onpointerdown={down} onpointermove={move} onpointerup={up} onpointercancel={up}
           onwheel={wheel}>
        {#each camera.grid.xs as x (x)}
          <line class="grid" class:axis={x === 0} x1={x} y1={vb.y} x2={x} y2={vb.y + vb.h}
                stroke-width={upp} />
        {/each}
        {#each camera.grid.ys as y (y)}
          <line class="grid" class:axis={y === 0} x1={vb.x} y1={y} x2={vb.x + vb.w} y2={y}
                stroke-width={upp} />
        {/each}

        <!-- Terrain first, at its true size, so everything else is read against it. -->
        {#each ph.shown.filter((o) => o.radius) as o (o.name)}
          {@const v = w2v(o.now.x, o.now.y)}
          <circle class="body-mark" cx={v.vx} cy={v.vy} r={o.radius} stroke-width={upp} />
        {/each}

        <!-- Real distances, so a blast covers the ground it actually took in. Under everything,
             since what it caught is drawn on top of it. -->
        {#each ph.explosions as b (`${b.x},${b.y}:${b.radius}`)}
          {@const v = w2v(b.x, b.y)}
          <circle class="blast {b.damage_type.toLowerCase()}" cx={v.vx} cy={v.vy} r={b.radius}
                  stroke-width={upp} />
        {/each}

        <!-- Under the markers, so a beam runs to the ship rather than over it. -->
        {#each ph.beams as b (`${b.x1},${b.y1}:${b.x2},${b.y2}`)}
          {@const from = w2v(b.x1, b.y1)}
          {@const to = w2v(b.x2, b.y2)}
          <line class="beam" x1={from.vx} y1={from.vy} x2={to.vx} y2={to.vy}
                stroke-width={1.6 * upp} />
        {/each}

        {#each ph.shown.filter((o) => !o.radius) as o (o.name)}
          {@const v = w2v(o.now.x, o.now.y)}
          {#if o.trail.length > 1}
            <polyline class="trail" class:seen={o.contact} points={trailOf(o)}
                      stroke={ph.colourOf(o)} stroke-width={1.4 * upp}
                      stroke-dasharray={o.contact ? `${5 * upp} ${5 * upp}` : null} />
          {/if}
          <polygon class="mark" class:named={NAMED.has(o.category_name)} class:seen={o.contact}
                   fill={ph.colourOf(o)}
                   points={markerFor(o.category_name, v.vx, v.vy, courseOf(o), upp)} />
          {#if o.killed}
            <path class="kill" d={burst(v.vx, v.vy, KILL_RADIUS)} stroke-width={1.4 * upp} />
            <circle class="kill-core" cx={v.vx} cy={v.vy} r={KILL_RADIUS * 0.18} />
          {/if}
        {/each}
      </svg>

      <!-- Text, in screen pixels, so it never scales. -->
      <svg class="text-layer" viewBox={`0 0 ${Math.max(1, camera.boxW)} ${Math.max(1, camera.boxH)}`}
           preserveAspectRatio="none" aria-hidden="true">
        {#each ph.shown.filter((o) => NAMED.has(o.category_name) || o.radius) as o (o.name)}
          {@const v = w2v(o.now.x, o.now.y)}
          <text class="label" class:seen={o.contact} fill={o.radius ? "#5c6784" : ph.colourOf(o)}
                x={camera.sx(v.vx) + 12} y={camera.sy(v.vy)} font-size="12.5">{o.name}</text>
        {/each}
        {#if camera.boxH}
          <line class="bar" x1="14" y1={camera.boxH - 18} x2={14 + camera.scaleBarPx} y2={camera.boxH - 18} />
          <text class="bar-label" x={14 + camera.scaleBarPx / 2} y={camera.boxH - 26}
                font-size="11" text-anchor="middle">{camera.grid.step}</text>
        {/if}
      </svg>

      <div class="zoom">
        <button type="button" onclick={() => camera.zoomBy(1 / 1.15)} aria-label="Zoom in">+</button>
        <button type="button" onclick={() => camera.zoomBy(1.15)} aria-label="Zoom out">−</button>
        <button type="button" onclick={fit}>Fit</button>
      </div>
    </div>

    <aside class="log" class:open={logOpen}>
      <h2>Round {ph.round} · tick {ph.tick}</h2>
      <div class="shown">
        <label>
          tail
          <select value={ph.tail} onchange={(e) => (ph.tail = Number(e.currentTarget.value))}>
            {#each TAILS as t (t)}<option value={t}>{t === 10 ? "a round" : `${t} tick${t === 1 ? "" : "s"}`}</option>{/each}
          </select>
        </label>
        <label>
          speed
          <select value={ph.perSecond} onchange={(e) => (ph.perSecond = Number(e.currentTarget.value))}>
            {#each SPEEDS as s (s)}<option value={s}>{s}/s</option>{/each}
          </select>
        </label>
      </div>
      <label><input type="checkbox" bind:checked={everyMessage} /> every message</label>
      {#if !lines.length}
        <p class="quiet">Nothing on this tick{everyMessage ? "" : " worth reading"}.</p>
      {:else}
        <ul>
          {#each lines as e, i (i)}
            <li class={e.kind}><span class="who">{e.who}</span>{e.text}</li>
          {/each}
        </ul>
      {/if}
    </aside>
  </div>

  <!-- The one line that is always on a phone's screen, so it carries where the playhead is: the
       transport under it is buttons and a scrub, and nothing to read. -->
  <button type="button" class="handle" aria-expanded={logOpen} onclick={() => (logOpen = !logOpen)}>
    <span>round <b>{ph.round}</b> · tick <b>{ph.tick}</b></span>
    <span class="chev">{lines.length || "nothing"} {logOpen ? "▼" : "▲"}</span>
  </button>

  <Transport {ph} />
</div>

<style>
  .replay { display: flex; flex-direction: column; height: 100%; }

  header {
    display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;
    padding: 12px 16px; border-bottom: 1px solid var(--edge);
    background: linear-gradient(#0d1322, var(--bg));
  }
  header h1 { margin: 0; font-size: 14px; font-weight: 600; letter-spacing: 0.16em;
              text-transform: uppercase; color: var(--hull); }
  .sub { font-size: 12px; color: var(--ink-dim); }
  .spacer { flex: 1; }
  /* Under the picker it belongs to, rather than under the game's name. */
  .legend { flex-basis: 100%; display: flex; flex-wrap: wrap; justify-content: flex-end;
            gap: 4px 14px; }
  .side { display: flex; align-items: center; gap: 5px; font-size: 11px; color: var(--ink-dim); }
  .side i { width: 9px; height: 9px; border-radius: 50%; }
  header select {
    font: inherit; font-size: 12px; color: var(--ink); background: #0d1320;
    border: 1px solid var(--edge); border-radius: 3px; padding: 5px 6px; min-height: 36px;
  }
  header select:hover { border-color: var(--cyan); }
  .back {
    font-family: var(--mono); font-size: 14px; color: var(--ink-dim);
    background: transparent; border: 1px solid var(--edge); border-radius: 3px;
    padding: 2px 9px; line-height: 1.3;
  }
  .back:hover { color: var(--cyan); border-color: var(--cyan); }

  .body { flex: 1; display: flex; min-height: 0; }
  .plot { position: relative; flex: 1; min-width: 0; min-height: 0; overflow: hidden;
          touch-action: none; overscroll-behavior: none;
          background: radial-gradient(120% 90% at 50% 50%, #0e1526 0%, #080b12 72%); }
  svg { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }
  .world { touch-action: none; cursor: grab; -webkit-user-select: none; user-select: none; }
  .world:active { cursor: grabbing; }
  .text-layer { pointer-events: none; }

  .overlay { position: absolute; inset: 0; margin: auto; height: fit-content; width: fit-content;
             color: var(--ink-dim); font-size: 13px; z-index: 3; }
  .overlay.err { color: var(--warn); }

  .grid { stroke: #16203a; }
  .grid.axis { stroke: #26375e; }
  .body-mark { fill: #1a2130; stroke: #2b3648; }
  .trail { fill: none; opacity: 0.45; }
  .mark { opacity: 0.7; }
  .mark.named { opacity: 1; }
  /* Something seen rather than known is drawn quieter, dashed, and at whatever bearing two
     sightings imply. It is a report, not a record. */
  .mark.seen { opacity: 0.5; }
  .trail.seen { opacity: 0.3; }
  .label.seen { opacity: 0.6; }
  .kill { stroke: var(--hit); fill: none; stroke-linecap: round; opacity: 0.9; }
  .kill-core { fill: var(--kill); }
  /* One tick's worth, so it reads as a flash rather than a line on the map. */
  .beam { stroke: var(--beam); opacity: 0.95; stroke-linecap: round; }
  /* A blast's colour answers what kind of harm it carried, and nothing else. A type this has
     never heard of is drawn as an ordinary explosion rather than not drawn at all. */
  .blast { fill: var(--hit); fill-opacity: 0.13; stroke: #04070d; }
  .blast.nanocyte { fill: var(--nanocyte); }
  .blast.emp { fill: var(--emp); }
  .label { font-family: var(--mono); dominant-baseline: middle; opacity: 0.9; }
  .bar { stroke: var(--ink-faint); stroke-width: 1; }
  .bar-label { font-family: var(--mono); fill: var(--ink-faint); }

  .zoom { position: absolute; top: 12px; left: 12px; display: flex; gap: 6px; z-index: 4; }
  .zoom button {
    font-family: var(--mono); font-size: 12px; color: var(--ink); min-height: 36px;
    background: rgba(13, 19, 32, 0.85); border: 1px solid var(--edge);
    padding: 5px 10px; border-radius: 3px;
  }
  .zoom button:hover { border-color: var(--cyan); color: var(--cyan); }

  .log { width: 300px; flex-shrink: 0; overflow-y: auto; padding: 14px 16px;
         border-left: 1px solid var(--edge); background: var(--panel); }
  .log h2 { margin: 0 0 10px; font-size: 11px; font-weight: 600; letter-spacing: 0.16em;
            text-transform: uppercase; color: var(--ink-dim); }
  .quiet { font-size: 11.5px; color: var(--ink-faint); margin: 0; }
  label { display: flex; align-items: center; gap: 6px; margin-bottom: 10px;
          font-size: 11px; color: var(--ink-dim); }
  input[type="checkbox"] { accent-color: var(--amber); }

  /* How the tick is drawn rather than what it says, so it sits with the message filter and not
     in the transport, which stays the size of the buttons a thumb actually presses. */
  .shown { display: flex; gap: 12px; margin-bottom: 10px; }
  .shown label { margin: 0; }
  select {
    font: inherit; font-size: 12px; color: var(--ink); background: #0d1320;
    border: 1px solid var(--edge); border-radius: 3px; padding: 6px 4px; min-height: 36px;
  }
  ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
  li { font-size: 11.5px; line-height: 1.45; color: var(--ink-dim); }
  li.hit { color: var(--hit); }
  li.explosion { color: var(--amber); }
  li.replenish { color: var(--ok); }
  .who { color: var(--cyan); margin-right: 6px; }

  /* Beside the picture there is always room for the log, so there is nothing to pull. */
  .handle { display: none; }

  /* Narrow enough that the log cannot sit beside the picture. Under it, a band deep enough to
     read is a third of the screen that the transport then has to share, so it becomes a drawer
     and the map keeps everything it is not using. */
  @media (max-width: 760px) {
    .body { flex-direction: column; }
    .log { display: none; width: auto; max-height: 45%;
           border-left: none; border-top: 1px solid var(--edge); }
    .log.open { display: block; }

    .handle {
      display: flex; align-items: center; justify-content: space-between; width: 100%;
      padding: 0 16px; min-height: 38px;
      font-family: var(--mono); font-size: 11.5px; color: var(--ink-dim);
      background: var(--panel); border: none; border-top: 1px solid var(--edge);
    }
    .handle b { color: var(--amber); font-weight: 400; }
    .handle .chev { color: var(--cyan); }
  }
</style>