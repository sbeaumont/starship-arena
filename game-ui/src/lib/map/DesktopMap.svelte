<script>
  import Plot from "./Plot.svelte";
  import LogPanel from "./LogPanel.svelte";
  import CourseTable from "./CourseTable.svelte";
  import { arcRange, w2v, ORDER_VERB } from "./plan.js";

  // The map with a mouse: everything at once, in three columns.
  let { planning, camera, layers, onRound, onLeave, onFit } = $props();

  // Collapsed by default: the map is what you want in front of you when planning.
  let showLog = $state(false);

  const plan = $derived(planning.plan);
  const ship = $derived(planning.ship);

  // On this side a lock only holds off the course; weapons stay settable, which is the whole
  // reason the button exists.
  const grabbable = $derived({
    path: planning.editable && !planning.locked.has(planning.selected),
    shots: planning.editable,
    ticks: true,
  });

  function centreOn(s) {
    const v = w2v(s.x, s.y);
    camera.centreOn(v.vx, v.vy);
  }

  async function ready() {
    const next = await planning.toggleReady();
    if (next !== null) onRound(next);
  }
</script>

<div class="console">
  <header>
    <button type="button" class="back" onclick={onLeave} title="Choose another game or player">←</button>
    <h1>Starship Arena</h1>
    <span class="sub">
      {#if plan}
        {plan.player} · faction {plan.factions.join(", ")} ·
        {#if planning.editable}planning round {plan.round + 1}{:else}after round {plan.round}{/if}
      {:else}loading…{/if}
    </span>
    <span class="spacer"></span>
    {#if plan}
      <span class="rounds">
        {#each Array(plan.last_round + 1) as _, r (r)}
          <button type="button" class="rbtn" class:on={r === plan.round}
                  onclick={() => onRound(r)}>{r}</button>
        {/each}
      </span>
    {/if}
    {#if planning.moved}
      <button type="button" class="badge moved" onclick={() => onRound(planning.moved)}>
        Round {planning.moved} has been played. Open it
      </button>
    {/if}
    {#if planning.aiming}<span class="badge aiming">click a target for {planning.aiming}</span>{/if}
    {#if plan && plan.state === "finished"}<span class="badge past">finished</span>
    {:else if plan && !planning.editable}<span class="badge past">read only</span>{/if}
    <span class="badge">{planning.game}</span>
  </header>

  <main>
    <aside class="log" class:open={showLog}>
      <button type="button" class="tab" onclick={() => (showLog = !showLog)}
              title={showLog ? "Hide the log" : "What happened this round"}>Log</button>
      {#if showLog}
        <div class="logbody"><LogPanel {planning} /></div>
      {/if}
    </aside>

    <Plot {planning} {camera} {layers} {grabbable}>
      <div class="zoom">
        <button type="button" onclick={() => camera.zoomBy(1 / 1.15)} aria-label="Zoom in">+</button>
        <button type="button" onclick={() => camera.zoomBy(1.15)} aria-label="Zoom out">−</button>
        <button type="button" onclick={onFit}>Fit</button>
      </div>
    </Plot>

    <aside class="panel">
      <section>
        <h2>Your ships</h2>
        <ul class="ships">
          {#each planning.ownShips as s (s.name)}
            <li>
              <button type="button" class="pick" class:on={s.name === planning.selected} class:gone={!s.alive}
                      onclick={() => { planning.selectShip(s.name); centreOn(s); }}>
                <span class="lamp" class:lit={s.player_ready}
                      title={s.player_ready ? "you said ready" : "you have not said ready"}></span>
                <span class="nm">{s.name}</span>
                <span class="ty">{s.ship_type}</span>
                <span class="sp">{s.speed}</span>
              </button>
            </li>
          {/each}
          {#if plan}
            {#each plan.ships.filter((s) => !s.owned) as s (s.name)}
              <li class="ally-row">
                <span class="lamp" class:lit={s.player_ready}
                      title={s.player ? `${s.player} is ${s.player_ready ? "ready" : "not ready"}` : ""}></span>
                <span class="nm">{s.name}</span><span class="ty">{s.player ?? s.ship_type}</span>
                {#if s.commands.length}
                  <span class="onmap" title="orders saved; their course and firing are on the map">plan</span>
                {/if}
              </li>
            {/each}
          {/if}
        </ul>
      </section>

      {#if ship}
        <section>
          <details class="fold">
            <summary>Specs · {ship.ship_type}</summary>
            <div class="specs">
              {#each Object.entries(ship.specs) as [k, v] (k)}
                <span class="sk">{k}</span><span class="sv">{v}</span>
              {/each}
            </div>
          </details>
        </section>

        <section>
          <h2>{ship.name} · course</h2>
          <CourseTable {planning} />

          {#if planning.editable}
            <div class="buttons">
              <button type="button" class="ghost-btn"
                      onclick={() => planning.resetCourse(planning.selected)}>Reset course</button>
              <button type="button" class="save" disabled={planning.sending}
                      onclick={() => planning.saveAll()}>Save all</button>
            </div>
            <div class="buttons">
              <button type="button" class="state" class:on={planning.locked.has(planning.selected)}
                      onclick={() => planning.toggleLock(planning.selected)}
                      title="Stop the course being dragged by accident. Weapons stay settable.">
                {planning.locked.has(planning.selected) ? "Unlock path" : "Lock path"}
              </button>
              <button type="button" class="state" class:on={planning.ready}
                      disabled={planning.settingReady} onclick={ready}
                      title="Tell the director you are done with this round">
                {planning.ready ? "Ready" : "Not ready"}
              </button>
            </div>
          {:else}
            <p class="note">Round {plan.round} has already been played. Go to round
              {plan.last_round} to give orders.</p>
          {/if}
          {#if planning.saveMsg}
            <p class="savemsg" class:err={planning.saveMsg.includes("REJECTED") || planning.saveMsg.includes("error")}
              >{planning.saveMsg}</p>
          {/if}
        </section>

        <section class="grow">
          {#if !planning.selectedTick}
            <h2>Orders</h2>
            <p class="hint">Click a joint on the course, or a tick number above, to give
              {ship.name} orders for that tick.</p>
          {:else}
            {@const tick = planning.selectedTick}
            <h2>Tick {tick} · orders</h2>
            <ul class="weapons">
              {#each ship.weapons as w (w.name)}
                {@const existing = planning.orderAt(tick, w.name)}
                {@const left = planning.ammoLeft(w)}
                <li class:armed={existing}>
                  <div class="wrow">
                    <span class="wname">{w.name}</span>
                    {#if !planning.editable}
                      <span></span>
                    {:else if existing}
                      <button type="button" class="wfire on"
                              onclick={() => planning.unarm(tick, w.name)}>clear</button>
                    {:else}
                      <button type="button" class="wfire"
                              disabled={(left !== null && left <= 0) || (w.inputs[0].choices?.length === 0)}
                              onclick={() => planning.arm(w)}>
                        {planning.aims(w) ? "pick target" : w.inputs[0].choices ? "choose" : "fire"}
                      </button>
                    {/if}
                    <span class="wammo" class:out={left !== null && left <= 0}>
                      {#if w.ammo !== null}{left}/{w.max_ammo} {w.payload}{/if}
                    </span>
                  </div>
                  {#if existing}
                    <div class="worder">
                      {#if w.inputs[0].choices}
                        <label class="slider">
                          {w.inputs[0].name}
                          <select value={existing[0]}
                                  onchange={(e) => planning.setParam(tick, w.name, 0, e.currentTarget.value)}>
                            {#each w.inputs[0].choices as c (c)}<option value={c}>{c}</option>{/each}
                          </select>
                        </label>
                        {#each w.inputs.slice(1) as inp, i (inp.name)}
                          <label class="slider aim">
                            {inp.name}
                            <input type="range" min={arcRange(w)[0]} max={arcRange(w)[1]} step="5"
                                   value={existing[i + 1]}
                                   oninput={(e) => planning.setParam(tick, w.name, i + 1, e.currentTarget.value)} />
                            <b>{existing[i + 1]}°</b>
                          </label>
                        {/each}
                      {:else if w.inputs[0].kind === "object_name"}
                        <span class="at">→ {existing[0]}</span>
                      {:else}
                        <label class="slider aim">
                          aim
                          <input type="range" min={arcRange(w)[0]} max={arcRange(w)[1]} step="5"
                                 value={existing[0]}
                                 oninput={(e) => planning.setParam(tick, w.name, 0, e.currentTarget.value)} />
                          <b>{existing[0]}°</b>
                        </label>
                        {#each w.inputs.slice(1) as inp, i (inp.name)}
                          <label class="slider">
                            {inp.name}
                            <input type="range" min={inp.min} max={inp.max} step="10"
                                   value={existing[i + 1]}
                                   oninput={(e) => planning.setParam(tick, w.name, i + 1, e.currentTarget.value)} />
                            <b>{existing[i + 1]}</b>
                          </label>
                        {/each}
                      {/if}
                    </div>
                  {/if}
                </li>
              {/each}
            </ul>
            {#if planning.orderableComponents.length}
              <ul class="weapons">
                {#each planning.orderableComponents as c (c.name)}
                  {@const existing = planning.compOrderAt(tick, c.name)}
                  <li class:armed={existing}>
                    <div class="wrow">
                      <span class="wname">{c.name}</span>
                      {#if !planning.editable}
                        <span></span>
                      {:else if existing}
                        <button type="button" class="wfire on"
                                onclick={() => planning.unarmComponent(tick, c.name)}>clear</button>
                      {:else}
                        <button type="button" class="wfire"
                                onclick={() => planning.armComponent(c)}>{ORDER_VERB[c.group].toLowerCase()}</button>
                      {/if}
                      <span class="wammo"></span>
                    </div>
                    {#if existing}
                      <div class="worder">
                        {#each c.inputs as inp, i (inp.name)}
                          <label class="slider">
                            {inp.name}
                            {#if inp.choices}
                              <select value={existing.params[i]}
                                      onchange={(e) => planning.setCompParam(tick, c.name, i, e.currentTarget.value)}>
                                {#each inp.choices as ch (ch)}<option value={ch}>{ch}</option>{/each}
                              </select>
                            {:else}
                              <input type="range" min={inp.min} max={inp.max} step="1"
                                     value={existing.params[i]}
                                     oninput={(e) => planning.setCompParam(tick, c.name, i, e.currentTarget.value)} />
                              <b>{existing.params[i]}</b>
                            {/if}
                          </label>
                        {/each}
                      </div>
                    {/if}
                  </li>
                {/each}
              </ul>
            {/if}
            <p class="note">One order per weapon per tick. Drag a shot's handle on the map to
              re-aim it; the arc turns with the course you plotted.</p>
          {/if}

          {#if planning.shipOrders?.other.length}
            <h2 class="spaced">Other orders</h2>
            <ul class="others">
              {#each planning.shipOrders.other as line, i (i)}<li>{line}</li>{/each}
            </ul>
          {/if}
        </section>
      {/if}

      <section>
        <h2>Layers</h2>
        <label><input type="checkbox" bind:checked={layers.grid} /> Grid &amp; origin</label>
        <label><input type="checkbox" bind:checked={layers.paths} /> Planned courses</label>
        <label><input type="checkbox" bind:checked={layers.fire} /> Weapon orders</label>
        <label><input type="checkbox" bind:checked={layers.scan} /> Scan range</label>
        <label><input type="checkbox" bind:checked={layers.tracks} /> Tracks</label>
        <label><input type="checkbox" bind:checked={layers.explosions} /> Explosions ({plan ? plan.explosions.length : 0})</label>
        <label><input type="checkbox" bind:checked={layers.hits} /> Hits ({plan ? plan.effects.length : 0})</label>
        <label><input type="checkbox" bind:checked={layers.enemyOrdnance} /> Enemy ordnance ({planning.counts.enemyOrd})</label>
        <label><input type="checkbox" bind:checked={layers.friendlyOrdnance} /> Friendly ordnance ({planning.counts.friendlyOrd})</label>
      </section>

      <section>
        {#if plan}
          <p class="tally">
            {planning.counts.ships} ships/bases (<span class="enemy-txt">{planning.counts.enemyShips} enemy</span>) ·
            {planning.counts.enemyOrd + planning.counts.friendlyOrd} ordnance
          </p>
        {/if}
        <details class="fold">
          <summary>Legend</summary>
          <ul class="legend">
            <li><span class="sw sel-sw"></span>ship being planned</li>
            <li><span class="sw own"></span>your other ships</li>
            <li><span class="sw course-sw"></span>their planned course</li>
            <li><span class="sw ally"></span>faction ally, and the plan they saved</li>
            <li><span class="sw enemy"></span>enemy contact</li>
            <li><span class="sw blast-sw"></span>explosion (true radius)</li>
          </ul>
          <p class="hint sub-hint">▲ course known · ◆ mine · ■ starbase · small ◆ seen once, course unknown</p>
        </details>
      </section>
    </aside>
  </main>
</div>

<style>
  .console { display: flex; flex-direction: column; height: 100%; min-height: 520px; }

  header {
    display: flex; align-items: baseline; gap: 14px;
    padding: 14px 20px; border-bottom: 1px solid var(--edge);
    background: linear-gradient(#0d1322, var(--bg));
  }
  header h1 { margin: 0; font-size: 15px; font-weight: 600; letter-spacing: 0.18em;
              text-transform: uppercase; color: var(--hull); }
  .sub { font-size: 12px; color: var(--ink-dim); letter-spacing: 0.06em; }
  .spacer { flex: 1; }
  .badge { font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--amber);
           border: 1px solid var(--amber); padding: 3px 8px; border-radius: 2px; opacity: 0.9; }
  .badge.aiming { color: var(--cyan); border-color: var(--cyan); }
  .badge.past { color: var(--ink-dim); border-color: var(--ink-faint); }
  .badge.moved { font-family: var(--mono); color: #79b894; border-color: #79b894;
                 background: #121c17; cursor: pointer; }
  .badge.moved:hover { filter: brightness(1.2); }

  .back {
    font-family: var(--mono); font-size: 14px; color: var(--ink-dim);
    background: transparent; border: 1px solid var(--edge); border-radius: 3px;
    padding: 2px 9px; cursor: pointer; line-height: 1.3;
  }
  .back:hover { color: var(--cyan); border-color: var(--cyan); }
  .back:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }

  .rounds { display: flex; gap: 3px; }
  .rbtn {
    font-family: var(--mono); font-size: 11px; color: var(--ink-dim);
    background: #0d1320; border: 1px solid var(--edge); border-radius: 3px;
    padding: 3px 8px; cursor: pointer; font-variant-numeric: tabular-nums;
  }
  .rbtn:hover { color: var(--cyan); border-color: var(--cyan); }
  .rbtn.on { color: var(--amber); border-color: var(--amber); }
  .rbtn:focus-visible { outline: 2px solid var(--cyan); outline-offset: 1px; }

  main { flex: 1; display: flex; min-height: 0; }

  /* The log, on the left, collapsed to a strip. */
  .log { display: flex; flex-shrink: 0; border-right: 1px solid var(--edge); background: var(--panel); }
  .log .tab {
    writing-mode: vertical-rl; text-orientation: mixed;
    padding: 14px 7px; border: none; background: transparent; cursor: pointer;
    font-family: var(--mono); font-size: 10px; letter-spacing: 0.18em; text-transform: uppercase;
    color: var(--ink-dim);
  }
  .log .tab:hover { color: var(--cyan); }
  .log.open .tab { color: var(--amber); }
  .log .tab:focus-visible { outline: 2px solid var(--cyan); outline-offset: -2px; }
  .logbody { width: 310px; overflow-y: auto; padding: 14px 16px 28px;
             border-left: 1px solid var(--edge); }

  .zoom { position: absolute; top: 12px; left: 12px; display: flex; gap: 6px; z-index: 4; }
  .zoom button {
    font-family: var(--mono); font-size: 12px; color: var(--ink);
    background: rgba(13, 19, 32, 0.85); border: 1px solid var(--edge);
    padding: 5px 10px; border-radius: 3px; cursor: pointer;
  }
  .zoom button:hover { border-color: var(--cyan); color: var(--cyan); }
  .zoom button:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }

  .panel { width: 340px; flex-shrink: 0; border-left: 1px solid var(--edge); background: var(--panel);
           display: flex; flex-direction: column; overflow-y: auto; }
  .panel section { padding: 16px 18px; border-bottom: 1px solid var(--edge); }
  .panel section.grow { flex: 1; }
  .panel h2 { margin: 0 0 10px; font-size: 11px; font-weight: 600; letter-spacing: 0.16em;
              text-transform: uppercase; color: var(--ink-dim); }
  .panel h2.spaced { margin-top: 20px; }

  .specs { display: grid; grid-template-columns: 88px 1fr; gap: 4px 10px; font-size: 11px; }
  .sk { color: var(--ink-faint); }
  .sv { color: var(--ink); font-variant-numeric: tabular-nums; }

  .hint { font-size: 12.5px; line-height: 1.55; margin: 0; }
  .sub-hint { margin-top: 10px; color: var(--ink-dim); font-size: 11.5px; }
  .note { font-size: 11.5px; color: var(--ink-dim); margin: 10px 0 0; line-height: 1.45; }

  .ships { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 3px; }
  .pick {
    width: 100%; display: flex; align-items: baseline; gap: 8px; text-align: left;
    font-family: var(--mono); font-size: 12.5px; color: var(--ink);
    background: #0d1320; border: 1px solid var(--edge); border-radius: 3px;
    padding: 6px 9px; cursor: pointer;
  }
  .pick:hover { border-color: var(--cyan); }
  .pick.on { border-color: var(--amber); color: var(--amber); }
  .pick.gone .nm { text-decoration: line-through; color: var(--ink-faint); }
  .pick:focus-visible { outline: 2px solid var(--cyan); outline-offset: 1px; }
  .pick .nm { flex: 1; }
  .pick .ty, .ally-row .ty { color: var(--ink-dim); font-size: 11px; }
  .pick .sp { font-variant-numeric: tabular-nums; }
  .ally-row { display: flex; gap: 8px; align-items: center; padding: 6px 9px; font-size: 12.5px;
              color: var(--cyan); opacity: 0.7; }
  .ally-row .nm { flex: 1; }
  .onmap { font-size: 9.5px; letter-spacing: 0.12em; text-transform: uppercase;
           border: 1px solid var(--cyan); border-radius: 2px; padding: 1px 4px; }

  /* Ready or not, per commander. Dim rather than red: not being ready yet is normal. */
  .lamp { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; background: var(--ghost); }
  .lamp.lit { background: #79b894; box-shadow: 0 0 5px rgba(121, 184, 148, 0.6); }

  .weapons { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
  .weapons li { border: 1px solid var(--edge); border-radius: 3px; padding: 7px 9px; background: #0d1320; }
  .weapons li.armed { border-color: var(--beam); }
  /* A name is the selector a player types, so it is never shortened: short codes like R1 hold the
     column at 30px and keep the buttons in line, a Shields or a Cloak pushes it out. */
  .wrow { display: grid; grid-template-columns: minmax(30px, auto) 74px 1fr; align-items: center;
          gap: 8px; font-size: 12.5px; }
  .wname { color: var(--hull); font-weight: 600; }
  .wammo { font-variant-numeric: tabular-nums; color: var(--cyan); font-size: 11.5px; }
  .wammo.out { color: var(--warn); }
  .wfire {
    font-family: var(--mono); font-size: 10.5px; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--ink); background: #121a2b;
    border: 1px solid var(--edge); border-radius: 3px; padding: 4px 0; cursor: pointer;
  }
  .wfire:hover:not(:disabled) { border-color: var(--beam); color: var(--beam); }
  .wfire:disabled { opacity: 0.35; cursor: not-allowed; }
  .wfire.on { border-color: var(--beam); color: var(--beam); }
  .worder { display: flex; align-items: center; gap: 10px; margin-top: 6px; flex-wrap: wrap; font-size: 12px; }
  .at { color: var(--beam); font-variant-numeric: tabular-nums; }
  .slider { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--ink-dim); padding: 0; }
  .slider input { width: 90px; accent-color: var(--beam); }
  .slider.aim { flex: 1 1 100%; }
  .slider.aim input { flex: 1; width: auto; }
  .slider b { color: var(--ink); font-variant-numeric: tabular-nums; }
  .slider select {
    flex: 1; min-width: 0; font: inherit; color: var(--ink); background: var(--panel);
    border: 1px solid var(--edge); border-radius: 3px; padding: 2px 4px;
  }

  .others { list-style: none; margin: 0; padding: 0; font-size: 12px; color: var(--ink-dim); }
  .others li { padding: 2px 0; }

  .legend { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px;
            font-size: 12px; color: var(--ink); }
  .legend li { display: flex; align-items: center; gap: 8px; }
  .sw { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .sw.own { background: var(--amber); opacity: 0.55; }
  .sw.sel-sw { background: var(--amber); }
  .sw.ally { background: var(--cyan); }
  .sw.enemy { background: var(--foe); }
  .sw.course-sw { background: var(--laid); }
  .sw.blast-sw { background: var(--hit); opacity: 0.35; border: 1px solid #04070d; }

  label { display: flex; align-items: center; gap: 8px; font-size: 12.5px; padding: 3px 0; cursor: pointer; }
  input[type="checkbox"] { accent-color: var(--amber); }

  .tally { margin: 0 0 12px; font-size: 12px; color: var(--ink-dim); }
  .enemy-txt { color: var(--foe); }

  .fold summary {
    cursor: pointer; font-size: 11px; font-weight: 600; letter-spacing: 0.16em;
    text-transform: uppercase; color: var(--ink-dim); list-style: none;
  }
  .fold summary::-webkit-details-marker { display: none; }
  .fold summary::before { content: "▸ "; }
  .fold[open] summary::before { content: "▾ "; }
  .fold summary:hover { color: var(--ink); }
  .fold summary:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }
  .fold[open] summary { margin-bottom: 10px; }

  .buttons { display: flex; gap: 8px; margin-top: 14px; }
  .buttons button {
    font-family: var(--mono); font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase;
    border: 1px solid var(--edge); padding: 8px 12px; border-radius: 3px; cursor: pointer; flex: 1;
  }
  .ghost-btn { color: var(--ink); background: #0d1320; }
  .ghost-btn:hover:not(:disabled) { border-color: var(--cyan); color: var(--cyan); }
  .save { color: #08111e; background: var(--amber); border-color: var(--amber); font-weight: 600; }
  .save:hover:not(:disabled) { filter: brightness(1.1); }
  .buttons button:disabled { opacity: 0.4; cursor: not-allowed; }
  .buttons button:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }

  /* Muted, because these sit at rest most of the time. */
  .state { color: #b07a80; background: #1a1218; border-color: #4a2f34; }
  .state:hover:not(:disabled) { filter: brightness(1.25); }
  .state.on { color: #79b894; background: #121c17; border-color: #2f4a3a; }

  .savemsg { margin: 8px 0 0; font-size: 11.5px; line-height: 1.45; color: var(--cyan); word-break: break-word; }
  .savemsg.err { color: var(--warn); }
</style>
