<script>
  // One chip per weapon, on or off for the tick being planned. A column narrow enough to leave
  // the map the screen: anything a chip cannot say goes on the bar underneath.
  let { planning } = $props();

  const tick = $derived(planning.selectedTick);
  const ship = $derived(planning.ship);
</script>

<div class="chips">
  {#each ship.weapons as w (w.name)}
    {@const on = planning.orderAt(tick, w.name)}
    {@const left = planning.ammoLeft(w)}
    <button type="button" class="chip" class:on={on} class:aiming={planning.aiming === w.name}
            disabled={!planning.editable || (!on && left !== null && left <= 0)
                      || (!on && w.inputs[0].choices?.length === 0)}
            onclick={() => (on ? planning.unarm(tick, w.name) : planning.arm(w))}>
      <span class="nm">{w.name}</span>
      {#if w.ammo !== null}<i class:out={left <= 0}>{left}</i>{/if}
    </button>
  {/each}
  {#each planning.orderableComponents as c (c.name)}
    {@const on = planning.compOrderAt(tick, c.name)}
    <button type="button" class="chip comp" class:on={on} disabled={!planning.editable}
            onclick={() => (on ? planning.unarmComponent(tick, c.name) : planning.armComponent(c))}>
      <span class="nm">{c.name}</span>
    </button>
  {/each}
</div>

<style>
  .chips {
    position: absolute; top: 8px; right: 8px; bottom: 8px; z-index: 5;
    display: flex; flex-direction: column; gap: 5px; align-items: flex-end;
    overflow-y: auto; overscroll-behavior: contain;
  }
  .chip {
    display: flex; align-items: center; justify-content: center; gap: 4px;
    min-width: 46px; min-height: 42px; padding: 0 8px; flex-shrink: 0;
    font-family: var(--mono); font-size: 12.5px; color: var(--ink);
    background: rgba(18, 26, 43, 0.94); border: 1px solid var(--edge); border-radius: 4px;
  }
  .chip:disabled { opacity: 0.35; }
  .chip.on { color: var(--beam); border-color: var(--beam); background: rgba(38, 33, 20, 0.96); }
  .chip.aiming { color: var(--cyan); border-color: var(--cyan); background: rgba(16, 32, 44, 0.96); }
  .chip.comp.on { color: var(--amber); border-color: var(--amber); background: rgba(31, 24, 8, 0.96); }
  .nm { white-space: nowrap; }
  .chip i { font-style: normal; font-size: 9.5px; color: var(--cyan);
            font-variant-numeric: tabular-nums; }
  .chip i.out { color: var(--warn); }
</style>
