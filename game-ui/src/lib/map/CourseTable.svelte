<script>
  // One row per tick of what the selected ship was told to do, and where that leaves it. The tick
  // number is how you reach a tick that has no node of its own to tap - a starbase never moves.
  let { planning } = $props();

  const ship = $derived(planning.ship);
  const orders = $derived(planning.shipOrders);
  const chain = $derived(planning.chain);
</script>

{#if ship && orders && chain}
  <table>
    <thead><tr><th class="t">Tick</th><th>Turn</th><th>Throttle</th><th>Speed</th><th>Orders</th></tr></thead>
    <tbody>
      {#each chain.slice(1) as n (n.t)}
        {@const fired = [...Object.keys(orders.fire[n.t] ?? {}), ...Object.keys(orders.comp[n.t] ?? {})]}
        <!-- The whole row picks the tick; the number stays a button so a keyboard can too. -->
        <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
        <tr class:idle={!orders.turn[n.t] && !orders.accel[n.t] && !fired.length}
            class:cur={n.t === planning.selectedTick}
            onclick={() => (planning.selectedTick = n.t)}>
          <td class="t">
            <button type="button" class="tick-pick"
                    onclick={() => (planning.selectedTick = n.t)}>{n.t}</button>
          </td>
          <td>
            {#if !orders.turn[n.t]}·{:else}
              <span class="turn" class:pinned={Math.abs(orders.turn[n.t]) >= ship.limits.max_turn}
                >{orders.turn[n.t] > 0 ? "R" : "L"}{Math.abs(orders.turn[n.t])}</span>
            {/if}
          </td>
          <td>
            {#if !orders.accel[n.t]}·{:else}
              <span class="accel" class:pinned={Math.abs(orders.accel[n.t]) >= ship.limits.max_delta_v}
                >A{orders.accel[n.t] > 0 ? "+" : ""}{orders.accel[n.t]}</span>
            {/if}
          </td>
          <td>{n.speed}</td>
          <td class="fire-cell">{fired.length ? fired.join(",") : "·"}</td>
        </tr>
      {/each}
    </tbody>
  </table>
  <p class="limits-line">
    limits: {ship.limits.max_turn}° turn · Δv {ship.limits.max_delta_v} ·
    max speed {ship.limits.max_speed}
  </p>
{/if}

<style>
  table { width: 100%; border-collapse: collapse; font-size: 12.5px; font-variant-numeric: tabular-nums; }
  th, td { text-align: right; padding: 3px 6px; }
  tbody tr { cursor: pointer; }
  tbody tr:hover { background: #131c2f; }
  th { font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--ink-dim);
       font-weight: 500; border-bottom: 1px solid var(--edge); }
  td.t, th.t { text-align: left; color: var(--ink-dim); }
  tr.idle td { color: var(--ink-faint); }
  tr.cur, tbody tr.cur:hover { background: #16203a; }
  .tick-pick {
    font-family: var(--mono); font-size: 12.5px; color: inherit; background: transparent;
    border: none; padding: 0 2px; cursor: pointer; text-decoration: underline dotted;
  }
  .tick-pick:hover { color: var(--cyan); }
  .fire-cell { color: var(--beam); text-align: left; font-size: 11px; }
  .turn { color: var(--cyan); }
  .accel { color: var(--amber); }
  .pinned { color: var(--warn); }
  .limits-line { margin: 8px 0 0; font-size: 11.5px; color: var(--ink-dim); }

  /* A row a thumb can hit. Ten of them still fit on the sheet at half height. */
  @media (pointer: coarse) {
    td { padding: 10px 6px; }
  }
</style>
