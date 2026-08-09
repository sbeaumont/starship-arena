<script>
  // What the round did to the ship you are looking at: where its condition stood when the round
  // opened, then one row per tick of what was done to it. Movement and energy are left out; the
  // map shows where it went, and the numbers show the rest.
  //
  // `parts` is for a shell with one panel per idea rather than one panel for both.
  let { planning, parts = "all" } = $props();

  let allShips = $state(false);
  let everyMessage = $state(false);

  // A full value only means something for a quantity: "3 Splinter" against a full "5 Splinter"
  // reads as "3/5 Splinter", while a state like a cloak's just reads as itself.
  function pairText(value, full) {
    if (value === full) return value;
    if (/^\d+$/.test(value) && /^\d+$/.test(full)) return `${value}/${full}`;
    const a = value.match(/^(\d+)\s+(.+)$/);
    const b = full.match(/^(\d+)\s+(.+)$/);
    return a && b && a[2] === b[2] ? `${a[1]}/${b[1]} ${a[2]}` : value;
  }

  // Scoped to the selected ship; the whole faction is several hundred lines a round.
  const byTick = $derived.by(() => {
    const plan = planning.plan;
    if (!plan) return [];
    const ships = allShips ? plan.ships : plan.ships.filter((s) => s.name === planning.selected);
    const rows = new Map();
    const row = (t) => {
      if (!rows.has(t)) rows.set(t, { tick: t, condition: null, events: [] });
      return rows.get(t);
    };
    for (const s of ships) {
      for (const e of s.events) {
        if (everyMessage || e.kind !== "internal") row(e.tick).events.push({ ship: s.name, ...e });
      }
      if (!allShips) for (const c of s.conditions) row(c.tick).condition = c;
    }
    return [...rows.values()].sort((a, b) => a.tick - b.tick);
  });

  const ship = $derived(planning.ship);
  const shows = (part) => parts === "all" || parts === part;
</script>

{#if planning.plan}
  {#if ship && shows("condition")}
    <h2>Condition at Tick 0</h2>
    <div class="gauge">
      <span class="gk">Hull</span>
      <span class="gbar"><i class:low={ship.hull / ship.max_hull < 0.34}
                            style="width: {(100 * ship.hull) / ship.max_hull}%"></i></span>
      <span class="gv">{ship.hull}/{ship.max_hull}</span>
    </div>
    <div class="gauge">
      <span class="gk">Battery</span>
      <span class="gbar"><i class="power"
                            style="width: {(100 * ship.battery) / ship.max_battery}%"></i></span>
      <span class="gv">{ship.battery}/{ship.max_battery}</span>
    </div>

    {#each ship.components as c (c.name)}
      <div class="comp">
        <span class="cn">{c.name}</span>
        <span class="cs">
          {#each Object.entries(c.status) as [k, v] (k)}
            <span class="pair" class:spent={v !== c.full[k]}>
              {pairText(v, c.full[k])}<span class="pk">{k}</span>
            </span>
          {/each}
        </span>
      </div>
    {/each}
  {/if}

  {#if shows("log")}
    <h2 class:spaced={ship && parts === "all"}>
      Round {planning.plan.round} · {allShips ? "faction" : (planning.selected ?? "no ship")}
    </h2>
    <label class="all"><input type="checkbox" bind:checked={allShips} /> all ships</label>
    <label class="all"><input type="checkbox" bind:checked={everyMessage} /> every message</label>
    {#if !byTick.length}
      <p class="note">{planning.selected ? "Nothing recorded." : "Pick a ship to read its log."}</p>
    {:else}
      {#each byTick as r (r.tick)}
        <div class="tickrow">
          <span class="t">{r.tick}</span>
          {#if r.condition}
            <span class="v">hull {r.condition.hull}</span>
            <span class="v">bat {r.condition.battery}</span>
            {#each Object.entries(r.condition.shields) as [q, s] (q)}
              <span class="v"><span class="q">{q}</span>{s}</span>
            {/each}
          {/if}
        </div>
        <ul>
          {#each r.events as e, i (i)}
            <li class={e.kind}>
              {#if allShips}<span class="who">{e.ship}</span>{/if}{e.text}
            </li>
          {/each}
        </ul>
      {/each}
    {/if}
  {/if}
{/if}

<style>
  h2 { margin: 0 0 8px; font-size: 11px; font-weight: 600; letter-spacing: 0.16em;
       text-transform: uppercase; color: var(--ink-dim); }
  h2.spaced { margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--edge); }

  /* Bars only where there is a numeric maximum: hull and battery. */
  .gauge { display: grid; grid-template-columns: 54px 1fr 72px; align-items: center;
           gap: 8px; margin-bottom: 6px; }
  .gk { font-size: 11px; color: var(--ink-dim); }
  .gbar { height: 5px; background: #0d1320; border: 1px solid var(--edge); border-radius: 3px;
          overflow: hidden; }
  .gbar i { display: block; height: 100%; background: #57d98a; }
  .gbar i.power { background: var(--cyan); }
  .gbar i.low { background: var(--warn); }
  .gv { font-size: 11px; color: var(--ink); text-align: right; font-variant-numeric: tabular-nums; }

  .comp { display: grid; grid-template-columns: 54px 1fr; gap: 8px; margin-top: 8px; }
  .cn { font-size: 11px; color: var(--ink-dim); }
  .cs { display: flex; flex-wrap: wrap; gap: 4px 10px; }
  .pair { font-size: 11px; color: var(--ink); white-space: nowrap; }
  .pair.spent { color: var(--amber); }
  .pk { color: var(--ink-faint); margin-left: 4px; }

  .tickrow { display: flex; flex-wrap: wrap; gap: 4px 8px; align-items: baseline;
             margin: 14px 0 4px; padding-top: 6px; border-top: 1px solid var(--edge); }
  .tickrow .t { color: var(--amber); font-size: 11px; min-width: 16px; font-variant-numeric: tabular-nums; }
  .tickrow .v { font-size: 10.5px; color: var(--ink-dim); font-variant-numeric: tabular-nums; }
  .tickrow .q { color: var(--ink-faint); margin-right: 2px; }

  ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 3px; }
  li { font-size: 11.5px; line-height: 1.45; color: var(--ink-dim); }
  li.hit { color: var(--warn); }
  li.explosion { color: var(--amber); }
  .who { color: var(--cyan); margin-right: 6px; }

  label.all { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--ink-dim);
              padding: 3px 0; cursor: pointer; }
  input[type="checkbox"] { accent-color: var(--amber); }
  .note { font-size: 11.5px; color: var(--ink-dim); margin: 10px 0 0; line-height: 1.45; }
</style>
