<script>
  import Plot from "./Plot.svelte";
  import LogPanel from "./LogPanel.svelte";
  import CourseTable from "./CourseTable.svelte";
  import Sheet from "./Sheet.svelte";
  import WeaponChips from "./WeaponChips.svelte";
  import WeaponBar from "./WeaponBar.svelte";
  import { w2v, canMove } from "./plan.js";

  // The map with fingers. One thing is unlocked at a time - a ship's course, or its weapons, or
  // neither - so every hit target on the map belongs to exactly one of them and can be as wide as
  // a fingertip.
  let { planning, camera, layers, onRound, onLeave, onFit } = $props();

  let mode = $state("view");     // view | path | weapons
  let drawer = $state(false);
  let ships = $state(false);     // the ship picker, above the bar
  let tab = $state(null);        // which sheet is open: ship | course | log

  const plan = $derived(planning.plan);
  const ship = $derived(planning.ship);

  // A mode only holds while it still has something to act on. Reaching a played round or picking
  // a starbase drops back to panning rather than leaving a button lit over dead handles.
  const active = $derived(
    !planning.editable ? "view"
    : mode === "path" && ship && !canMove(ship) ? "view"
    : mode
  );

  const grabbable = $derived({
    path: active === "path",
    shots: active === "weapons",
    ticks: active === "weapons",
  });

  // Weapons needs a tick to act on, and a starbase never gives you a node to tap for one.
  $effect(() => {
    if (active === "weapons" && planning.plan && !planning.selectedTick) planning.selectedTick = 1;
  });

  function setMode(next) {
    mode = mode === next ? "view" : next;
    planning.aiming = null;
  }

  function pick(s) {
    planning.selectShip(s.name);
    const v = w2v(s.x, s.y);
    camera.centreOn(v.vx, v.vy);
    ships = false;
  }

  async function ready() {
    const next = await planning.toggleReady();
    if (next !== null) onRound(next);
  }

  const rounds = $derived(plan ? plan.last_round : 0);
  const goRound = (r) => { if (r >= 0 && r <= rounds) onRound(r); };
</script>

<div class="shell">
  <header>
    <button type="button" class="burger" onclick={() => (drawer = true)} aria-label="Menu">
      <span></span><span></span><span></span>
    </button>
    <span class="who">
      {#if plan}
        <b>{ship?.name ?? plan.player}</b>
        {#if planning.editable}planning {plan.round + 1}{:else}after {plan.round}{/if}
      {:else}loading…{/if}
    </span>
    {#if planning.moved}
      <button type="button" class="badge moved" onclick={() => onRound(planning.moved)}>
        R{planning.moved} played
      </button>
    {:else if plan && plan.state === "finished"}
      <span class="badge past">finished</span>
    {:else if plan && !planning.editable}
      <span class="badge past">read only</span>
    {:else if plan}
      <button type="button" class="ready" class:on={planning.ready} disabled={planning.settingReady}
              onclick={ready}
              title={planning.ready ? "You have said ready. Tap to take it back."
                                    : "Tell the director you are done with this round"}>
        {planning.ready ? "Ready ✓" : "Ready"}
      </button>
    {/if}
  </header>

  <Plot {planning} {camera} {layers} {grabbable} coarse>
    <button type="button" class="fit" onclick={onFit}>Fit</button>

    {#if active === "weapons" && ship && planning.selectedTick}
      <WeaponChips {planning} />
    {/if}
  </Plot>

  {#if active === "weapons" && ship && planning.selectedTick}
    <WeaponBar {planning} />
  {/if}

  {#if planning.aiming}
    <div class="aim-banner">
      <span>Tap a target for <b>{planning.aiming}</b></span>
      <button type="button" onclick={() => (planning.aiming = null)}>cancel</button>
    </div>
  {/if}

  {#if planning.saveMsg}
    <p class="toast" class:err={planning.saveMsg.includes("REJECTED") || planning.saveMsg.includes("error")}>
      <span>{planning.saveMsg}</span>
      <button type="button" onclick={() => (planning.saveMsg = "")} aria-label="Dismiss">×</button>
    </p>
  {/if}

  {#if ships}
    <div class="picker">
      {#each planning.ownShips as s (s.name)}
        <button type="button" class="prow" class:on={s.name === planning.selected}
                class:gone={!s.alive} onclick={() => pick(s)}>
          <span class="lamp" class:lit={s.player_ready}></span>
          <span class="nm">{s.name}</span>
          <span class="ty">{s.ship_type}</span>
          <span class="sp">{s.speed}</span>
        </button>
      {/each}
      {#if plan}
        {#each plan.ships.filter((s) => !s.owned) as s (s.name)}
          <span class="prow ally">
            <span class="lamp" class:lit={s.player_ready}></span>
            <span class="nm">{s.name}</span>
            <span class="ty">{s.player ?? s.ship_type}</span>
          </span>
        {/each}
      {/if}
    </div>
  {/if}

  <nav class="bar">
    <button type="button" class="chip" onclick={() => (ships = !ships)}>
      {ship?.name ?? "—"}<i class:up={ships}>▾</i>
    </button>
    <button type="button" class="mode" class:on={active === "path"}
            disabled={!planning.editable || !ship || !canMove(ship)}
            onclick={() => setMode("path")}>Path</button>
    <button type="button" class="mode" class:on={active === "weapons"}
            disabled={!planning.editable || !ship}
            onclick={() => setMode("weapons")}>Weapons</button>
    <span class="gap"></span>
    <button type="button" class="save" class:dirty={planning.dirty}
            disabled={!planning.editable || planning.sending}
            onclick={() => planning.saveAll()}>Save</button>
  </nav>

  <Sheet tabs={["Ship", "Course", "Log"]} bind:open={tab}>
    {#if tab === "ship"}
      {#if ship}
        <h2>{ship.name} · {ship.ship_type}</h2>
        <div class="specs">
          {#each Object.entries(ship.specs) as [k, v] (k)}
            <span class="sk">{k}</span><span class="sv">{v}</span>
          {/each}
        </div>
      {/if}
      <LogPanel {planning} parts="condition" />
    {:else if tab === "course"}
      <CourseTable {planning} />
      {#if planning.editable && ship}
        <button type="button" class="wide"
                onclick={() => planning.resetCourse(planning.selected)}>Reset course</button>
      {/if}
      {#if planning.shipOrders?.other.length}
        <h2 class="spaced">Other orders</h2>
        <ul class="others">
          {#each planning.shipOrders.other as line, i (i)}<li>{line}</li>{/each}
        </ul>
      {/if}
    {:else if tab === "log"}
      <LogPanel {planning} parts="log" />
    {/if}
  </Sheet>
</div>

{#if drawer}
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <div class="scrim" onclick={() => (drawer = false)}></div>
  <aside class="drawer">
    <button type="button" class="close" onclick={() => (drawer = false)} aria-label="Close">×</button>

    <!-- Where you can go, first: the way out of a game should not be at the end of a scroll. -->
    <section class="nav">
      <button type="button" class="wide" onclick={onLeave}>← All games</button>
      <button type="button" class="wide" onclick={() => window.open("/api/game/manual", "_blank")}>Manual</button>
    </section>

    <section>
      <h2>Round</h2>
      <div class="stepper">
        <button type="button" onclick={() => goRound((plan?.round ?? 0) - 1)}
                disabled={!plan || plan.round === 0} aria-label="Previous round">‹</button>
        <span>{plan ? plan.round : "—"} <i>of {rounds}</i></span>
        <button type="button" onclick={() => goRound((plan?.round ?? 0) + 1)}
                disabled={!plan || plan.round >= rounds} aria-label="Next round">›</button>
      </div>
    </section>

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
      <h2>Legend</h2>
      <ul class="legend">
        <li><span class="sw sel-sw"></span>ship being planned</li>
        <li><span class="sw own"></span>your other ships</li>
        <li><span class="sw course-sw"></span>their planned course</li>
        <li><span class="sw ally"></span>faction ally</li>
        <li><span class="sw enemy"></span>enemy contact</li>
        <li><span class="sw blast-sw"></span>explosion (true radius)</li>
      </ul>
      <p class="hint">▲ course known · ◆ mine · ■ starbase · small ◆ seen once, course unknown</p>
    </section>
  </aside>
{/if}

<style>
  .shell { display: flex; flex-direction: column; height: 100%; background: var(--bg);
           overflow: hidden; }

  header {
    display: flex; align-items: center; gap: 10px; flex-shrink: 0;
    padding: 6px 10px; padding-top: max(6px, env(safe-area-inset-top));
    border-bottom: 1px solid var(--edge); background: linear-gradient(#0d1322, var(--bg));
  }
  .burger {
    display: flex; flex-direction: column; justify-content: center; gap: 4px;
    width: 40px; height: 40px; padding: 0 9px; flex-shrink: 0;
    background: transparent; border: none; cursor: pointer;
  }
  .burger span { display: block; height: 2px; background: var(--ink); border-radius: 1px; }
  .who { flex: 1; min-width: 0; font-size: 12px; color: var(--ink-dim);
         white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .who b { color: var(--amber); font-weight: 600; margin-right: 6px; }
  .badge { font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; padding: 4px 7px;
           border-radius: 2px; border: 1px solid var(--amber); color: var(--amber); flex-shrink: 0; }
  .badge.past { color: var(--ink-dim); border-color: var(--ink-faint); }
  .badge.moved { color: #79b894; border-color: #79b894; background: #121c17; }

  /* Saying you are done belongs where you can see it, not down a menu. It is a toggle, so a
     mis-tap is undone by the same button. */
  .ready {
    flex-shrink: 0; min-height: 38px; padding: 0 12px; border-radius: 4px;
    font-family: var(--mono); font-size: 11.5px; letter-spacing: 0.08em; text-transform: uppercase;
    color: #b07a80; background: #1a1218; border: 1px solid #4a2f34;
  }
  .ready.on { color: #0c1710; background: #79b894; border-color: #79b894; font-weight: 600; }
  .ready:disabled { opacity: 0.5; }

  .fit {
    position: absolute; top: 10px; left: 10px; z-index: 4;
    font-family: var(--mono); font-size: 12px; color: var(--ink);
    background: rgba(13, 19, 32, 0.85); border: 1px solid var(--edge);
    padding: 9px 14px; border-radius: 3px;
  }

  /* Above the bar rather than over the map: the strip it was started from is out on the right,
     and a banner that has to dodge it has nowhere left to put the words. */
  .aim-banner {
    flex-shrink: 0; display: flex; align-items: center; gap: 10px;
    padding: 9px 12px; background: #0d1a22; border-top: 1px solid var(--cyan);
    color: var(--cyan); font-size: 12.5px;
  }
  .aim-banner span { flex: 1; }
  .aim-banner button {
    font-family: var(--mono); font-size: 11px; text-transform: uppercase; color: var(--ink-dim);
    background: transparent; border: 1px solid var(--edge); border-radius: 3px; padding: 5px 10px;
  }

  .toast {
    flex-shrink: 0; display: flex; align-items: center; gap: 10px; margin: 0;
    padding: 8px 12px; font-size: 11.5px; line-height: 1.4; color: var(--cyan);
    background: #0d1320; border-top: 1px solid var(--edge); word-break: break-word;
  }
  .toast.err { color: var(--warn); }
  .toast span { flex: 1; }
  .toast button { background: transparent; border: none; color: inherit; font-size: 18px;
                  padding: 0 6px; line-height: 1; }

  /* The ship picker sits on the bar it was opened from, so the map keeps as much height as it
     can while it is up. */
  .picker {
    flex-shrink: 0; max-height: 40vh; overflow-y: auto; overscroll-behavior: contain;
    background: var(--panel); border-top: 1px solid var(--edge);
  }
  .prow {
    width: 100%; display: flex; align-items: center; gap: 10px; text-align: left;
    font-family: var(--mono); font-size: 14px; color: var(--ink);
    background: transparent; border: none; border-bottom: 1px solid var(--edge);
    padding: 12px 14px;
  }
  .prow.on { color: var(--amber); background: #16203a; }
  .prow.gone .nm { text-decoration: line-through; color: var(--ink-faint); }
  .prow.ally { color: var(--cyan); opacity: 0.7; }
  .prow .nm { flex: 1; }
  .prow .ty { color: var(--ink-dim); font-size: 11.5px; }
  .prow .sp { font-variant-numeric: tabular-nums; font-size: 12px; }
  .lamp { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; background: var(--ghost); }
  .lamp.lit { background: #79b894; box-shadow: 0 0 5px rgba(121, 184, 148, 0.6); }

  .bar {
    display: flex; align-items: stretch; gap: 6px; flex-shrink: 0; padding: 7px 8px;
    background: var(--panel); border-top: 1px solid var(--edge);
  }
  .bar button {
    font-family: var(--mono); font-size: 12px; letter-spacing: 0.06em; text-transform: uppercase;
    color: var(--ink); background: #0d1320; border: 1px solid var(--edge); border-radius: 4px;
    padding: 0 13px; min-height: 44px;
  }
  .bar button:disabled { opacity: 0.3; }
  .gap { flex: 1; }
  .chip { display: flex; align-items: center; gap: 6px; max-width: 40%; color: var(--amber) !important;
          border-color: #4a3a20 !important; }
  .chip i { font-style: normal; font-size: 9px; transition: transform 0.12s; }
  .chip i.up { transform: rotate(180deg); }
  .mode.on { color: var(--amber); border-color: var(--amber); background: #1a1408; }
  .save.dirty { color: #08111e; background: var(--amber); border-color: var(--amber); font-weight: 600; }

  .scrim { position: fixed; inset: 0; background: rgba(4, 7, 13, 0.65); z-index: 20; }
  .drawer {
    position: fixed; top: 0; left: 0; bottom: 0; width: min(310px, 84vw); z-index: 21;
    background: var(--panel); border-right: 1px solid var(--edge);
    overflow-y: auto; overscroll-behavior: contain;
    padding-top: env(safe-area-inset-top); padding-bottom: env(safe-area-inset-bottom);
    animation: slide 0.16s ease-out;
  }
  @keyframes slide { from { transform: translateX(-100%); } to { transform: none; } }
  .close { position: absolute; top: 6px; right: 6px; width: 40px; height: 40px;
           background: transparent; border: none; color: var(--ink-dim); font-size: 24px; }
  .drawer section { padding: 14px 16px; border-bottom: 1px solid var(--edge); }
  .drawer h2 { margin: 0 0 10px; font-size: 11px; font-weight: 600; letter-spacing: 0.16em;
               text-transform: uppercase; color: var(--ink-dim); }
  .drawer section.nav { padding-top: 46px; }

  .stepper { display: flex; align-items: center; gap: 8px; }
  .stepper button {
    width: 48px; min-height: 44px; font-size: 20px; color: var(--ink);
    background: #0d1320; border: 1px solid var(--edge); border-radius: 4px;
  }
  .stepper button:disabled { opacity: 0.3; }
  .stepper span { flex: 1; text-align: center; font-variant-numeric: tabular-nums; font-size: 15px; }
  .stepper i { color: var(--ink-faint); font-style: normal; font-size: 12px; }

  .wide {
    display: block; width: 100%; min-height: 46px; font-family: var(--mono); font-size: 12.5px;
    letter-spacing: 0.06em; text-transform: uppercase; border-radius: 4px;
    border: 1px solid var(--edge); background: #0d1320; color: var(--ink); margin-top: 8px;
  }
  .nav .wide:first-of-type { margin-top: 0; }

  .drawer label { display: flex; align-items: center; gap: 10px; font-size: 13.5px;
                  padding: 7px 0; }
  .drawer input[type="checkbox"] { width: 18px; height: 18px; accent-color: var(--amber); }

  .legend { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 7px;
            font-size: 12.5px; color: var(--ink); }
  .legend li { display: flex; align-items: center; gap: 9px; }
  .sw { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .sw.own { background: var(--amber); opacity: 0.55; }
  .sw.sel-sw { background: var(--amber); }
  .sw.ally { background: var(--cyan); }
  .sw.enemy { background: var(--foe); }
  .sw.course-sw { background: var(--laid); }
  .sw.blast-sw { background: var(--hit); opacity: 0.35; border: 1px solid #04070d; }
  .hint { margin: 10px 0 0; font-size: 11.5px; line-height: 1.5; color: var(--ink-dim); }

  /* sheet contents */
  h2 { margin: 0 0 10px; font-size: 11px; font-weight: 600; letter-spacing: 0.16em;
       text-transform: uppercase; color: var(--ink-dim); }
  h2.spaced { margin-top: 20px; }
  .specs { display: grid; grid-template-columns: 1fr auto; gap: 5px 12px; font-size: 12.5px;
           margin-bottom: 18px; }
  .sk { color: var(--ink-faint); }
  .sv { color: var(--ink); font-variant-numeric: tabular-nums; }
  .others { list-style: none; margin: 0; padding: 0; font-size: 12.5px; color: var(--ink-dim); }
  .others li { padding: 3px 0; }
</style>
