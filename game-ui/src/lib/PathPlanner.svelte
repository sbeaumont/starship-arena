<script>
  import { onMount } from "svelte";

  // ===== Which ship we're planning (hardcoded for now; the API is live) =====
  const GAME = "xke";
  const SHIP = "TheGalaxy";
  const N = 10; // a round is 10 ticks

  // ===== World <-> screen mapping. Origin (the ship "now") sits at screen centre,
  //       north is up, and the view stays world-fixed (north-up). =====
  const OX = 450, OY = 360, SCALE = 0.75;
  const sx = (x) => OX + x * SCALE;
  const sy = (y) => OY - y * SCALE;

  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const normDelta = (d) => ((d + 180) % 360 + 360) % 360 - 180;
  const rad = (d) => (d * Math.PI) / 180;

  // ===== Live data, filled in by the fetch on mount =====
  let loading = $state(true);
  let error = $state(null);
  let round = $state(0);
  let shipLabel = $state("");
  let start = $state({ heading: 0, speed: 0 });                 // the ship's current vector
  let limits = $state({ max_turn: 35, max_delta_v: 25, max_speed: 45 });
  let saveMsg = $state("");

  // ===== The plan: a turn + throttle delta per tick (reactive) =====
  let turn = $state(Array(N + 1).fill(0));
  let accel = $state(Array(N + 1).fill(0));

  // ===== Derived: the node chain, re-simulated on any change to plan/start/limits =====
  const nodes = $derived.by(() => {
    const out = [{ t: 0, x: 0, y: 0, heading: start.heading, speed: start.speed, atLimit: false }];
    let h = start.heading, s = start.speed, x = 0, y = 0;
    for (let t = 1; t <= N; t++) {
      h += turn[t];
      s = clamp(s + accel[t], 0, limits.max_speed);
      x += Math.sin(rad(h)) * s;
      y += Math.cos(rad(h)) * s;
      const atLimit =
        Math.abs(turn[t]) >= limits.max_turn || Math.abs(accel[t]) >= limits.max_delta_v || s >= limits.max_speed;
      out.push({ t, x, y, heading: h, speed: s, atLimit });
    }
    return out;
  });

  const pathPts = $derived(nodes.map((n) => `${sx(n.x)},${sy(n.y)}`).join(" "));

  // The untouched continuation of the current vector, and the ship marker.
  const ghostPts = $derived.by(() => {
    const pts = []; let h = start.heading, s = start.speed, x = 0, y = 0;
    pts.push(`${sx(x)},${sy(y)}`);
    for (let t = 1; t <= N; t++) { x += Math.sin(rad(h)) * s; y += Math.cos(rad(h)) * s; pts.push(`${sx(x)},${sy(y)}`); }
    return pts.join(" ");
  });
  const shipPts = $derived.by(() => {
    const hd = rad(start.heading);
    return [
      [sx(0) + Math.sin(hd) * 15, sy(0) - Math.cos(hd) * 15],
      [sx(0) + Math.sin(hd + 2.5) * 9, sy(0) - Math.cos(hd + 2.5) * 9],
      [sx(0) + Math.sin(hd - 2.5) * 9, sy(0) - Math.cos(hd - 2.5) * 9],
    ].map((p) => p.join(",")).join(" ");
  });

  const rings = [50, 100, 150, 200, 250, 300];

  // ===== Load the real ship on mount (its last completed round = its current vector) =====
  onMount(async () => {
    try {
      const games = await (await fetch("/api/game/games")).json();
      const g = games.find((x) => x.name === GAME);
      const r = Math.max(1, (g ? g.current_round : 2) - 1);
      const res = await fetch(`/api/game/${GAME}/ships/${SHIP}/rounds/${r}`);
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      const d = await res.json();
      const last = d.ticks[d.ticks.length - 1];   // end-of-round state = current vector
      start = { heading: last.heading, speed: last.speed };
      limits = d.limits;
      round = r;
      shipLabel = `${d.ship} · ${d.ship_type}`;
    } catch (e) {
      error = String(e);
    } finally {
      loading = false;
    }
  });

  // ===== Dragging (unchanged mechanic, now bounded by the live limits) =====
  let svgEl;
  let dragIdx = null;

  function toWorld(evt) {
    const pt = svgEl.createSVGPoint();
    pt.x = evt.clientX; pt.y = evt.clientY;
    const u = pt.matrixTransform(svgEl.getScreenCTM().inverse());
    return { x: (u.x - OX) / SCALE, y: (OY - u.y) / SCALE };
  }

  function grab(i, evt) { dragIdx = i; svgEl.setPointerCapture(evt.pointerId); }

  function drag(evt) {
    if (dragIdx === null) return;
    const prev = nodes[dragIdx - 1];
    const w = toWorld(evt);
    const dx = w.x - prev.x, dy = w.y - prev.y;
    const dh = clamp(normDelta((Math.atan2(dx, dy) * 180) / Math.PI - prev.heading), -limits.max_turn, limits.max_turn);
    const dv = clamp(Math.hypot(dx, dy) - prev.speed, -limits.max_delta_v, limits.max_delta_v);
    const newSpeed = clamp(prev.speed + dv, 0, limits.max_speed);
    turn[dragIdx] = Math.round(dh);
    accel[dragIdx] = Math.round(newSpeed - prev.speed);
    saveMsg = "";
  }

  function release(evt) {
    if (dragIdx !== null) { try { svgEl.releasePointerCapture(evt.pointerId); } catch (_) {} }
    dragIdx = null;
  }

  function reset() { turn = Array(N + 1).fill(0); accel = Array(N + 1).fill(0); saveMsg = ""; }

  // ===== Turn the plan into command lines and POST them to the real engine =====
  function planLines() {
    const lines = [];
    for (let t = 1; t <= N; t++) {
      if (turn[t]) lines.push(`${t}: ${turn[t] > 0 ? "R" : "L"}${Math.abs(turn[t])}`);
      if (accel[t]) lines.push(`${t}: A${accel[t]}`);
    }
    return lines;
  }

  async function send() {
    const lines = planLines();
    saveMsg = "Sending…";
    try {
      const res = await fetch(`/api/game/${GAME}/ships/${SHIP}/commands`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lines }),
      });
      const body = await res.json();
      saveMsg = body.ok
        ? `Accepted — ${lines.length} command${lines.length === 1 ? "" : "s"} saved for round ${round + 1}.`
        : `Rejected: ${body.checks.filter((c) => !c.ok).map((c) => c.line).join("; ")}`;
    } catch (e) {
      saveMsg = `Error: ${e}`;
    }
  }
</script>

<div class="console">
  <header>
    <h1>Plotting Console</h1>
    <span class="sub">{shipLabel || "loading…"}{round ? ` · after round ${round}` : ""}</span>
    <span class="spacer"></span>
    <span class="badge">live · {GAME}</span>
  </header>

  <main>
    <div class="plot">
      {#if loading}
        <p class="overlay">Loading {SHIP} from the game API…</p>
      {:else if error}
        <p class="overlay err">Couldn't reach the API: {error}<br />Is the FastAPI server running on :8000?</p>
      {/if}
      <svg bind:this={svgEl} viewBox="0 0 900 720" preserveAspectRatio="xMidYMid meet"
           role="img" aria-label="Ship trajectory. Drag a node to re-plan the path."
           onpointermove={drag} onpointerup={release} onpointercancel={release}>
        {#each rings as r}
          <circle class="ring" cx={OX} cy={OY} r={r * SCALE} />
        {/each}
        <line class="ref" x1={OX} y1={OY} x2={OX} y2={sy(320)} />
        <polyline class="ghost" points={ghostPts} />
        <polyline class="path" points={pathPts} />
        <polygon class="hull" points={shipPts} />
        {#each nodes.slice(1) as n (n.t)}
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <!-- pointer-only drag handle; keyboard planning is a later feature -->
          <circle class="hit" cx={sx(n.x)} cy={sy(n.y)} r="14" onpointerdown={(e) => grab(n.t, e)} />
          <circle class="node" class:limit={n.atLimit} cx={sx(n.x)} cy={sy(n.y)} r="6" />
          <text class="tlabel" x={sx(n.x) + 11} y={sy(n.y) + 4}>{n.t}</text>
        {/each}
      </svg>
    </div>

    <aside class="panel">
      <section>
        <h2>How to fly it</h2>
        <p class="hint">
          The ship's current vector is loaded <b>live</b> from the game. Drag a
          <b>node</b>: it pivots around the one before it and everything downstream
          swings along. A joint at its limit turns <span class="warn">red</span>.
          <b>Send</b> pushes the plan through the real engine's validation.
        </p>
      </section>

      <section>
        <h2>Ship limits</h2>
        <div class="limits">
          <div class="lim"><span class="val">{limits.max_turn}&deg;</span><span class="cap">max turn</span></div>
          <div class="lim"><span class="val">{limits.max_delta_v}</span><span class="cap">max &Delta;v</span></div>
          <div class="lim"><span class="val">{limits.max_speed}</span><span class="cap">max speed</span></div>
        </div>
      </section>

      <section class="grow">
        <h2>Derived commands</h2>
        <table>
          <thead>
            <tr><th class="t">Tick</th><th>Turn</th><th>Throttle</th><th>Speed</th></tr>
          </thead>
          <tbody>
            {#each nodes.slice(1) as n (n.t)}
              {@const tr = turn[n.t]}
              {@const av = accel[n.t]}
              <tr class:idle={tr === 0 && av === 0}>
                <td class="t">{n.t}</td>
                <td>{#if tr === 0}·{:else}<span class="turn" class:pinned={Math.abs(tr) >= limits.max_turn}>{tr > 0 ? "R" : "L"}{Math.abs(tr)}</span>{/if}</td>
                <td>{#if av === 0}·{:else}<span class="accel" class:pinned={Math.abs(av) >= limits.max_delta_v}>A{av > 0 ? "+" : ""}{av}</span>{/if}</td>
                <td>{n.speed}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </section>

      <footer>
        <div class="buttons">
          <button type="button" class="ghost-btn" onclick={reset}>Reset</button>
          <button type="button" class="send" onclick={send} disabled={loading || !!error}>Send to ship</button>
        </div>
        {#if saveMsg}<p class="savemsg" class:err={saveMsg.startsWith("Rejected") || saveMsg.startsWith("Error")}>{saveMsg}</p>{/if}
      </footer>
    </aside>
  </main>
</div>

<style>
  .console { display: flex; flex-direction: column; height: 100%; min-height: 520px; }

  header {
    display: flex; align-items: baseline; gap: 14px;
    padding: 14px 20px; border-bottom: 1px solid var(--edge);
    background: linear-gradient(#0d1322, #0a0e17);
  }
  header h1 { margin: 0; font-size: 15px; font-weight: 600; letter-spacing: 0.18em; text-transform: uppercase; color: var(--hull); }
  .sub { font-size: 12px; color: var(--ink-dim); letter-spacing: 0.06em; }
  .spacer { flex: 1; }
  .badge { font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--amber); border: 1px solid var(--amber); padding: 3px 8px; border-radius: 2px; opacity: 0.9; }

  main { flex: 1; display: flex; min-height: 0; }

  .plot { position: relative; flex: 1; min-width: 0; background: radial-gradient(120% 90% at 50% 50%, #0e1526 0%, #080b12 72%); }
  svg { width: 100%; height: 100%; display: block; touch-action: none; }

  .overlay {
    position: absolute; inset: 0; margin: auto; height: fit-content; width: fit-content; max-width: 70%;
    text-align: center; color: var(--ink-dim); font-size: 13px; line-height: 1.6; z-index: 2;
  }
  .overlay.err { color: var(--warn); }

  .ring { fill: none; stroke: var(--ring); stroke-width: 1; opacity: 0.5; }
  .ref { stroke: var(--grid); stroke-width: 1; stroke-dasharray: 3 6; }
  .ghost { fill: none; stroke: var(--ghost); stroke-width: 1.5; stroke-dasharray: 2 7; }
  .path { fill: none; stroke: var(--amber); stroke-width: 2.5; stroke-linejoin: round; }
  .hull { fill: var(--hull); }
  .hit { fill: transparent; cursor: grab; }
  .hit:active { cursor: grabbing; }
  .node { fill: #0a0e17; stroke: var(--cyan); stroke-width: 2; pointer-events: none; }
  .node.limit { stroke: var(--warn); }
  .tlabel { fill: var(--ink-dim); font-size: 11px; pointer-events: none; font-family: var(--mono); }

  .panel { width: 320px; flex-shrink: 0; border-left: 1px solid var(--edge); background: var(--panel); display: flex; flex-direction: column; overflow-y: auto; }
  .panel section { padding: 16px 18px; border-bottom: 1px solid var(--edge); }
  .panel section.grow { flex: 1; }
  .panel h2 { margin: 0 0 10px; font-size: 11px; font-weight: 600; letter-spacing: 0.16em; text-transform: uppercase; color: var(--ink-dim); }

  .hint { font-size: 12.5px; line-height: 1.55; margin: 0; }
  .hint b { color: var(--amber); font-weight: 600; }
  .warn { color: var(--warn); }

  .limits { display: flex; gap: 18px; }
  .lim { display: flex; flex-direction: column; gap: 2px; }
  .val { font-size: 18px; color: var(--hull); font-variant-numeric: tabular-nums; }
  .cap { font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--ink-dim); }

  table { width: 100%; border-collapse: collapse; font-size: 13px; font-variant-numeric: tabular-nums; }
  th, td { text-align: right; padding: 4px 6px; }
  th { font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--ink-dim); font-weight: 500; border-bottom: 1px solid var(--edge); }
  td.t, th.t { text-align: left; color: var(--ink-dim); }
  tr.idle td { color: var(--ink-faint); }
  .turn { color: var(--cyan); }
  .accel { color: var(--amber); }
  .pinned { color: var(--warn); }

  footer { padding: 12px 18px; display: flex; flex-direction: column; gap: 10px; }
  .buttons { display: flex; gap: 8px; }
  button {
    font-family: var(--mono); font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase;
    border: 1px solid var(--edge); padding: 8px 14px; border-radius: 3px; cursor: pointer; flex: 1;
    transition: border-color 0.15s, color 0.15s, background 0.15s;
  }
  .ghost-btn { color: var(--ink); background: #0d1320; }
  .ghost-btn:hover { border-color: var(--cyan); color: var(--cyan); }
  .send { color: #08111e; background: var(--amber); border-color: var(--amber); font-weight: 600; }
  .send:hover:not(:disabled) { filter: brightness(1.1); }
  .send:disabled { opacity: 0.4; cursor: not-allowed; }
  button:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }

  .savemsg { margin: 0; font-size: 12px; line-height: 1.4; color: var(--cyan); }
  .savemsg.err { color: var(--warn); }

  @media (max-width: 760px) {
    main { flex-direction: column; }
    .panel { width: auto; border-left: none; border-top: 1px solid var(--edge); }
  }
  @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>