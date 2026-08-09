<script>
  let types = $state([]);
  let loading = $state(true);
  let error = $state(null);

  $effect(() => {
    (async () => {
      try {
        const res = await fetch("/api/game/ship-types");
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        types = await res.json();
      } catch (e) {
        error = String(e);
      } finally {
        loading = false;
      }
    })();
  });

  // Grouped by the category each type answers with, so a new kind of object needs nothing here.
  const groups = $derived.by(() => {
    const by = new Map();
    for (const t of types) {
      if (!by.has(t.category)) by.set(t.category, []);
      by.get(t.category).push(t);
    }
    return [...by.entries()];
  });
</script>

<div class="screen">
  <header>
    <h1>Ships</h1>
    <p class="sub">Every model in the registry, with what it carries. Stats are public: the
      game is won by flying well, not by knowing something the others do not.</p>
  </header>

  {#if loading}
    <p class="msg">Loading…</p>
  {:else if error}
    <p class="msg err">Couldn't reach the API: {error}</p>
  {:else}
    {#each groups as [category, models] (category)}
      <h2>{category}</h2>
      <div class="cards">
        {#each models as t (t.type_name)}
          <article>
            <h3>{t.name}</h3>
            <div class="rows">
              {#each Object.entries(t.specs) as [k, v] (k)}
                <span class="k">{k}</span><span class="v">{v}</span>
              {/each}
            </div>
          </article>
        {/each}
      </div>
    {/each}
  {/if}
</div>

<style>
  .screen {
    height: 100%; overflow-y: auto; padding: 40px 32px;
    background: radial-gradient(120% 90% at 50% 0%, #0e1526 0%, #080b12 70%);
  }
  header, h2, .cards { max-width: 1000px; margin-left: auto; margin-right: auto; }
  header { margin-bottom: 28px; }
  h1 { margin: 10px 0 0; font-size: 19px; font-weight: 600; letter-spacing: 0.2em;
       text-transform: uppercase; color: var(--hull); }
  .sub { margin: 8px 0 0; font-size: 13px; color: var(--ink-dim); max-width: 62ch; line-height: 1.5; }
  h2 { margin: 26px auto 10px; font-size: 11px; font-weight: 600; letter-spacing: 0.16em;
       text-transform: uppercase; color: var(--ink-dim); }


  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(270px, 1fr)); gap: 12px; }
  article { background: var(--panel); border: 1px solid var(--edge); border-radius: 4px;
            padding: 14px 16px; }
  h3 { margin: 0 0 10px; font-size: 13px; font-weight: 600; color: var(--amber);
       letter-spacing: 0.04em; }

  .rows { display: grid; grid-template-columns: 84px 1fr; gap: 3px 10px; font-size: 11px; }
  .k { color: var(--ink-faint); }
  .v { color: var(--ink); font-variant-numeric: tabular-nums; }

  .msg { max-width: 1000px; margin: 0 auto; font-size: 13px; color: var(--ink-dim); }
  .msg.err { color: var(--warn); }
</style>