<script>
  import { N, directionIndex, coneInput } from "./plan.js";

  // Which tick the chips are setting, and the one thing a handle on the map cannot say: which
  // wreck, which quadrant, how much power. Under the map rather than over it, so a slider has
  // room to be dragged.
  let { planning } = $props();

  const tick = $derived(planning.selectedTick);
  const ship = $derived(planning.ship);

  // Which of a weapon's inputs the handle already sets: the direction it is aimed, and the width
  // a scanner's handle is pulled out to.
  function extras(w) {
    const dir = directionIndex(w);
    const cone = coneInput(w) ? 1 : -1;
    return w.inputs.map((inp, i) => ({ inp, i })).filter(({ i }) => i !== dir && i !== cone);
  }

  const rows = $derived.by(() => {
    const out = [];
    for (const w of ship.weapons) {
      const on = planning.orderAt(tick, w.name);
      if (!on) continue;
      for (const { inp, i } of extras(w)) {
        out.push({ key: `${w.name}:${inp.name}`, owner: w.name, inp, value: on[i],
                   set: (v) => planning.setParam(tick, w.name, i, v) });
      }
    }
    for (const c of planning.orderableComponents) {
      const on = planning.compOrderAt(tick, c.name);
      if (!on) continue;
      c.inputs.forEach((inp, i) => {
        out.push({ key: `${c.name}:${inp.name}`, owner: c.name, inp, value: on.params[i],
                   set: (v) => planning.setCompParam(tick, c.name, i, v) });
      });
    }
    return out;
  });

  // The chip that is lit says whose these are. Only when two things are armed at once does a
  // row have to name itself.
  const named = $derived(new Set(rows.map((r) => r.owner)).size > 1);

  const step = (d) => (planning.selectedTick = Math.min(N, Math.max(1, tick + d)));
</script>

<div class="wbar">
  <div class="ticks">
    <button type="button" onclick={() => step(-1)} disabled={tick <= 1} aria-label="Earlier tick">‹</button>
    <span>{tick}</span>
    <button type="button" onclick={() => step(1)} disabled={tick >= N} aria-label="Later tick">›</button>
  </div>

  {#if rows.length}
    <div class="rows">
      {#each rows as r (r.key)}
        <div class="row">
          {#if named}<span class="rk">{r.owner}</span>{/if}
          {#if r.inp.choices?.length}
            {#if r.inp.choices.length <= 4 && r.inp.choices.every((c) => c.length <= 3)}
              <div class="seg">
                {#each r.inp.choices as c (c)}
                  <button type="button" class:on={String(r.value) === c} onclick={() => r.set(c)}>{c}</button>
                {/each}
              </div>
            {:else}
              <select value={r.value} onchange={(e) => r.set(e.currentTarget.value)}>
                {#each r.inp.choices as c (c)}<option value={c}>{c}</option>{/each}
              </select>
            {/if}
          {:else if r.inp.kind === "object_name"}
            <span class="at">{r.value ? `→ ${r.value}` : "tap a target"}</span>
          {:else}
            <input type="range" min={r.inp.min} max={r.inp.max} step="1" value={r.value}
                   oninput={(e) => r.set(e.currentTarget.value)} />
            <b>{r.value}</b>
          {/if}
        </div>
      {/each}
    </div>
  {:else}
    <span class="hint">Tap a weapon, drag its handle to aim.</span>
  {/if}
</div>

<style>
  /* Nothing in here may push the bar wider than the screen, so every box is allowed to shrink:
     a flex child keeps its content width until min-width says otherwise. */
  .wbar {
    flex-shrink: 0; display: flex; align-items: center; gap: 8px; min-width: 0;
    padding: 5px 8px; background: #0d1320; border-top: 1px solid var(--edge);
  }

  .ticks { display: flex; align-items: center; gap: 2px; flex-shrink: 0; }
  .ticks button {
    width: 30px; height: 36px; font-size: 16px; color: var(--ink);
    background: #121a2b; border: 1px solid var(--edge); border-radius: 4px;
  }
  .ticks button:disabled { opacity: 0.3; }
  .ticks span { min-width: 22px; text-align: center; font-size: 13px; color: var(--amber);
                font-variant-numeric: tabular-nums; }

  .rows { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
  .row { display: flex; align-items: center; gap: 6px; min-width: 0; }
  .rk { flex: 0 1 auto; min-width: 0; font-size: 10px; color: var(--ink-dim);
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .seg { flex: 1 1 auto; min-width: 0; display: flex; gap: 3px; }
  .seg button {
    flex: 1 1 0; min-width: 0; min-height: 34px; font-family: var(--mono); font-size: 12px;
    color: var(--ink); background: #121a2b; border: 1px solid var(--edge); border-radius: 4px;
  }
  .seg button.on { color: var(--amber); border-color: var(--amber); background: #1f1808; }

  select {
    flex: 1 1 0; min-width: 0; min-height: 34px; font: inherit; font-size: 12.5px;
    color: var(--ink); background: #121a2b; border: 1px solid var(--edge); border-radius: 4px;
    padding: 0 6px;
  }

  input[type="range"] { flex: 1 1 0; min-width: 0; height: 34px; accent-color: #ff7b7b; }
  b { flex-shrink: 0; min-width: 30px; text-align: right; font-size: 12.5px; color: var(--ink);
      font-variant-numeric: tabular-nums; }
  .at { flex: 1 1 auto; min-width: 0; font-size: 12.5px; color: #ff9d9d;
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .hint { flex: 1 1 0; min-width: 0; font-size: 11px; color: var(--ink-faint);
          overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
