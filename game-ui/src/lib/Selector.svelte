<script>
  let { onPick } = $props();

  let games = $state([]);
  let overview = $state(null);
  let game = $state(null);
  let loading = $state(true);
  let loadingOverview = $state(false);
  let error = $state(null);

  $effect(() => {
    (async () => {
      try {
        const res = await fetch("/api/game/games");
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        // A game that has been set up can be played: at round 0 there is nothing to look
        // back on yet, but that is exactly when the first round gets planned.
        games = (await res.json()).filter((g) => g.current_round > 0);
      } catch (e) {
        error = String(e);
      } finally {
        loading = false;
      }
    })();
  });

  // You open a *player's* view and plan all of their ships in it, so the overview groups a
  // faction's ships under whoever commands them rather than listing them flat.
  function commandersOf(faction) {
    const by = new Map();
    for (const s of faction.ships) {
      const key = s.player ?? "";
      if (!by.has(key)) by.set(key, []);
      by.get(key).push(s);
    }
    return [...by.entries()]
      .map(([player, ships]) => ({
        player: player || null,
        ships,
        score: ships.reduce((sum, s) => sum + s.score, 0),
        waiting: ships.filter((s) => s.alive && !s.orders_in).length,
        lost: ships.every((s) => !s.alive),
      }))
      .sort((a, b) => b.score - a.score || (a.player ?? "").localeCompare(b.player ?? ""));
  }

  async function chooseGame(name) {
    game = name;
    overview = null;
    loadingOverview = true;
    try {
      const res = await fetch(`/api/game/${name}/overview`);
      overview = res.ok ? await res.json() : null;
    } finally {
      loadingOverview = false;
    }
  }
</script>

<div class="screen">
  <header>
    <h1>Starship Arena</h1>
    <p class="sub">Choose a game, then whose view to open.</p>
  </header>

  {#if loading}
    <p class="msg">Loading games…</p>
  {:else if error}
    <p class="msg err">Couldn't reach the API: {error}</p>
  {:else}
    <div class="cols">
      <section class="games">
        <h2>Game</h2>
        <ul>
          {#each games as g (g.name)}
            <li>
              <button type="button" class="pick" class:on={g.name === game}
                      onclick={() => chooseGame(g.name)}>
                <span class="nm">{g.name}</span>
                <span class="meta">
                  {g.current_round === 1 ? "not played yet" : `${g.current_round - 1} rounds played`}
                </span>
              </button>
            </li>
          {/each}
        </ul>
      </section>

      <section class="detail">
        {#if !game}
          <h2>Factions</h2>
          <p class="msg quiet">Pick a game first.</p>
        {:else if loadingOverview}
          <h2>Factions</h2>
          <p class="msg quiet">Loading {game}…</p>
        {:else if !overview}
          <h2>Factions</h2>
          <p class="msg quiet">Nothing to show for {game}.</p>
        {:else}
          <h2>{game} — planning round {overview.last_round + 1}, best first</h2>
          {#each overview.factions as f, rank (f.name)}
            <div class="faction">
              <div class="fhead">
                <span class="rank">{rank + 1}</span>
                <span class="fname">Faction {f.name}</span>
                <span class="fscore">{f.score}</span>
              </div>
              {#each commandersOf(f) as c (c.player ?? "unassigned")}
                {#if c.ships.length === 1}
                  <!-- One ship, one row: grouping a single ship under a header is just noise. -->
                  {@const s = c.ships[0]}
                  <button type="button" class="ship" disabled={!c.player}
                          onclick={() => onPick(game, c.player)}
                          title={c.player ? `Open ${c.player}'s view` : "No player commands this ship"}>
                    <span class="dot" class:in={s.orders_in} class:dead={!s.alive}
                          title={!s.alive ? "destroyed" : s.orders_in ? "orders handed in" : "waiting for orders"}
                    ></span>
                    <span class="nm" class:gone={!s.alive}>{s.name}</span>
                    <span class="ty">{s.ship_type}</span>
                    <span class="pl">{c.player ?? "—"}</span>
                    <span class="sc">{s.score}</span>
                  </button>
                {:else}
                  <!-- A whole fleet under one player, since opening them plans all of it. -->
                  <div class="commander">
                    <!-- Same columns as a single-ship row, so the player name and score line
                         up whichever shape a game happens to have. -->
                    <button type="button" class="ship fleet" disabled={!c.player}
                            onclick={() => onPick(game, c.player)}
                            title={c.player
                              ? `Open ${c.player}'s view and plan all ${c.ships.length} of their ships`
                              : "No player commands these"}>
                      <span class="dot" class:in={c.waiting === 0} class:dead={c.lost}
                            title={c.lost ? "all ships lost"
                                   : c.waiting === 0 ? "all orders handed in"
                                   : `${c.waiting} still to plan`}></span>
                      <span class="nm">{c.ships.map((s) => s.name).join(", ")}</span>
                      <span class="pl">{c.player ?? "unassigned"}</span>
                      <span class="sc">{c.score}</span>
                    </button>
                    <ul class="ships">
                      {#each c.ships as s (s.name)}
                        <li class="shiprow">
                          <span class="dot small" class:in={s.orders_in} class:dead={!s.alive}
                                title={!s.alive ? "destroyed" : s.orders_in ? "orders handed in" : "waiting for orders"}
                          ></span>
                          <span class="nm" class:gone={!s.alive}>{s.name}</span>
                          <span class="ty">{s.ship_type}</span>
                          <span class="sc">{s.score}</span>
                        </li>
                      {/each}
                    </ul>
                  </div>
                {/if}
              {/each}
            </div>
          {/each}
          <p class="key">
            <span class="dot in"></span> orders in ·
            <span class="dot"></span> waiting ·
            <span class="dot dead"></span> destroyed
          </p>
        {/if}
      </section>
    </div>
    <p class="honour">
      Opening a player plans all of their ships together in one view.
      There is no login yet: please look only at your own ships while a round is open.
    </p>
  {/if}
</div>

<style>
  .screen {
    height: 100%; overflow-y: auto; padding: 40px 32px;
    background: radial-gradient(120% 90% at 50% 0%, #0e1526 0%, #080b12 70%);
  }
  header, .cols, .honour { max-width: 1000px; margin-left: auto; margin-right: auto; }
  header { margin-bottom: 28px; }
  h1 { margin: 0; font-size: 19px; font-weight: 600; letter-spacing: 0.2em;
       text-transform: uppercase; color: var(--hull); }
  .sub { margin: 8px 0 0; font-size: 13px; color: var(--ink-dim); }

  .cols { display: flex; gap: 28px; align-items: flex-start; }
  .games { width: 230px; flex-shrink: 0; }
  .detail { flex: 1; min-width: 0; }
  h2 { margin: 0 0 10px; font-size: 11px; font-weight: 600; letter-spacing: 0.16em;
       text-transform: uppercase; color: var(--ink-dim); }

  ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 3px; }

  .pick {
    width: 100%; display: flex; flex-direction: column; gap: 2px; text-align: left;
    font-family: var(--mono); font-size: 13px; color: var(--ink);
    background: #0d1320; border: 1px solid var(--edge); border-radius: 3px;
    padding: 8px 11px; cursor: pointer; transition: border-color 0.15s, color 0.15s;
  }
  .pick:hover { border-color: var(--cyan); color: var(--cyan); }
  .pick.on { border-color: var(--amber); color: var(--amber); }
  .pick:focus-visible { outline: 2px solid var(--cyan); outline-offset: 1px; }
  .meta { font-size: 11px; color: var(--ink-dim); }

  .faction { margin-bottom: 18px; }
  .fhead { display: flex; align-items: baseline; gap: 10px; padding: 0 0 6px;
           border-bottom: 1px solid var(--edge); margin-bottom: 6px; }
  .rank { font-size: 11px; color: var(--ink-faint); font-variant-numeric: tabular-nums;
          min-width: 14px; }
  .fname { font-size: 12.5px; color: var(--hull); font-weight: 600; letter-spacing: 0.06em; }
  .fscore { margin-left: auto; font-size: 12.5px; color: var(--amber);
            font-variant-numeric: tabular-nums; }

  /* A player with a single ship: one flat row, as informative as a group would be. */
  .ship {
    width: 100%; display: flex; align-items: center; gap: 10px; text-align: left;
    font-family: var(--mono); font-size: 12.5px; color: var(--ink);
    background: #0d1320; border: 1px solid var(--edge); border-radius: 3px;
    padding: 6px 10px; margin-bottom: 3px; cursor: pointer; transition: border-color 0.15s;
  }
  .ship:hover:not(:disabled) { border-color: var(--cyan); }
  .ship:disabled { opacity: 0.5; cursor: default; }
  .ship:focus-visible { outline: 2px solid var(--cyan); outline-offset: 1px; }
  .ship .nm { min-width: 120px; color: var(--hull); }
  .ship .ty { flex: 1; color: var(--ink-dim); font-size: 11px; }
  .ship .pl { min-width: 90px; color: var(--cyan); }
  .nm.gone { color: var(--ink-faint); text-decoration: line-through; }

  .commander { margin-bottom: 8px; }
  /* A fleet row is the same row, listing its ships where a single ship's name would be. There
     is no type column to show for a fleet, so the names take that width and wrap onto as many
     lines as they need; the other columns stay centred as the row grows. */
  .ship.fleet .nm { flex: 1; line-height: 1.5; }
  .ship.fleet .pl { font-weight: 600; }

  .ships { margin: 2px 0 0; padding: 0 0 0 22px; gap: 0; }
  .shiprow { display: flex; align-items: center; gap: 9px; padding: 3px 10px;
             font-size: 11.5px; color: var(--ink-dim); }
  .shiprow .nm { min-width: 120px; color: var(--ink); }
  .shiprow .nm.gone { color: var(--ink-faint); text-decoration: line-through; }
  .shiprow .ty { flex: 1; font-size: 11px; }
  .sc { min-width: 40px; text-align: right; font-variant-numeric: tabular-nums; }

  .dot {
    width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0;
    background: var(--warn);           /* waiting for orders */
  }
  .dot.in { background: #57d98a; }     /* handed in */
  .dot.dead { background: var(--ink-faint); }
  .dot.small { width: 6px; height: 6px; }

  .key { display: flex; align-items: center; gap: 6px; margin: 14px 0 0;
         font-size: 11.5px; color: var(--ink-dim); }
  .key .dot { margin-left: 6px; }

  .msg { font-size: 13px; color: var(--ink); line-height: 1.6; }
  .msg.err { color: var(--warn); }
  .msg.quiet { color: var(--ink-faint); }
  .honour { margin-top: 28px; font-size: 11.5px; color: var(--ink-faint); }

  @media (max-width: 820px) {
    .cols { flex-direction: column; }
    .games { width: auto; }
  }
</style>
