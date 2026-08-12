<script>
  // The clock and who is signed in belong to the chrome above; this screen is handed the skew
  // and the ticking now, so its countdowns cannot disagree with the bar's clock.
  let { me, directing, skew, nowMs, onPick, onPage, onReplay } = $props();

  let allGames = $state([]);
  // Kept apart from the shared games rather than mixed in: it is nobody else's, it waits for
  // nobody, and a director's list would otherwise fill up with other people's practice.
  let solo = $state(null);
  let overview = $state(null);
  const games = $derived(directing
    ? allGames
    : allGames.filter((g) => me.games.includes(g.name)));
  let game = $state(null);
  let loading = $state(true);
  let loadingOverview = $state(false);
  let error = $state(null);

  // Narrow enough and the standings open under the game they belong to, which is the only place
  // there is room for them. Matches the breakpoint the stylesheet stacks at.
  const stacked = matchMedia("(max-width: 820px)");
  let inline = $state(stacked.matches);
  $effect(() => {
    const on = (e) => (inline = e.matches);
    stacked.addEventListener("change", on);
    return () => stacked.removeEventListener("change", on);
  });

  function whenLocal(iso) {
    const at = new Date(iso);
    const today = new Date(nowMs + skew).toDateString() === at.toDateString();
    const hm = at.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    return today ? hm : `${at.toLocaleDateString([], { weekday: "short" })} ${hm}`;
  }

  function until(iso) {
    const mins = Math.round((Date.parse(iso) - (nowMs + skew)) / 60000);
    if (mins <= 0) return "due now";
    if (mins < 60) return `in ${mins} min`;
    const hours = Math.floor(mins / 60);
    return mins % 60 ? `in ${hours}h ${mins % 60}m` : `in ${hours}h`;
  }

  $effect(() => {
    (async () => {
      const mine = await fetch("/api/game/solo");
      if (mine.ok) solo = await mine.json();
    })();
  });

  $effect(() => {
    (async () => {
      try {
        const res = await fetch("/api/game/games");
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        // A game that has been set up can be played: at round 0 there is nothing to look
        // back on yet, but that is exactly when the first round gets planned.
        allGames = (await res.json()).filter((g) => g.current_round > 0);
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
        // Saving and saying ready are both things a commander does once, for their whole fleet.
        saved: ships.every((s) => !s.alive || s.orders_in),
        ready: ships[0].player_ready,
        lost: ships.every((s) => !s.alive),
      }))
      .sort((a, b) => b.score - a.score || (a.player ?? "").localeCompare(b.player ?? ""));
  }

  const pct = (n, of) => (of ? Math.round((100 * n) / of) : 0);

  // The standings are everyone's to read; only your own view is yours to open.
  const canOpen = (player) => !!player && (directing || player === me.name);

  // A game that is not yours makes no sense to keep open once you drop to a player's view.
  $effect(() => {
    if (!directing && game && !me.games.includes(game)) {
      game = null;
      overview = null;
    }
  });

  // Tapping the game you already have open shuts it, so a list of games reads as a list rather
  // than as something that only ever grows.
  async function chooseGame(name) {
    overview = null;
    if (game === name) {
      game = null;
      return;
    }
    game = name;
    loadingOverview = true;
    try {
      const res = await fetch(`/api/game/${name}/overview`);
      overview = res.ok ? await res.json() : null;
    } finally {
      loadingOverview = false;
    }
  }
</script>

{#snippet status(done, lost, doneWord, owedWord)}
  <span class="st" class:ok={done} class:out={lost}>
    <span class="dot" class:filled={done && !lost} class:none={lost}></span>
    <span class="long">{lost ? "—" : done ? doneWord : owedWord}</span>
  </span>
{/snippet}

{#snippet standings()}
  {#if loadingOverview}
    <p class="msg quiet">Loading {game}…</p>
  {:else if !overview}
    <p class="msg quiet">Nothing to show for {game}.</p>
  {:else}
    <!-- Whoever asks gets the war they were in: a commander their own side and what it saw, the
         director every side at once. -->
    <button type="button" class="replay" onclick={() => onReplay(game)}>▶ Replay tick by tick</button>
    {#each overview.factions as f, rank (f.name)}
      <div class="faction">
        <div class="fhead">
          <span class="rank">{rank + 1}</span>
          <span class="fname">Faction {f.name}</span>
          <span class="fscore">{f.score}</span>
          <span class="st head" title="orders saved"><span class="long">saved</span><span class="short">S</span></span>
          <span class="st head" title="said ready"><span class="long">ready</span><span class="short">R</span></span>
        </div>
        {#each commandersOf(f) as c (c.player ?? "unassigned")}
          {#if c.ships.length === 1}
            <!-- One ship, one row: grouping a single ship under a header is just noise. -->
            {@const s = c.ships[0]}
            <button type="button" class="ship" disabled={!canOpen(c.player)}
                    onclick={() => onPick(game, c.player)}
                    title={canOpen(c.player) ? `Open ${c.player}'s view` : "Not yours to open"}>
              <span class="nm" class:gone={!s.alive}>{s.name}</span>
              <span class="ty">{s.ship_type}</span>
              <span class="pl">{c.player ?? "—"}</span>
              <span class="sc">{s.score}</span>
              {@render status(c.saved, c.lost, "saved", "waiting")}
              {@render status(c.ready, c.lost, "ready", "not yet")}
            </button>
          {:else}
            <!-- A whole fleet under one player, since opening them plans all of it. -->
            <div class="commander">
              <!-- Same columns as a single-ship row, so the player name and score line up
                   whichever shape a game happens to have. -->
              <button type="button" class="ship fleet" disabled={!canOpen(c.player)}
                      onclick={() => onPick(game, c.player)}
                      title={canOpen(c.player)
                        ? `Open ${c.player}'s view and plan all ${c.ships.length} of their ships`
                        : "Not yours to open"}>
                <span class="nm">{c.ships.map((s) => s.name).join(", ")}</span>
                <span class="pl">{c.player ?? "unassigned"}</span>
                <span class="sc">{c.score}</span>
                {@render status(c.saved, c.lost, "saved", "waiting")}
                {@render status(c.ready, c.lost, "ready", "not yet")}
              </button>
              <ul class="ships">
                {#each c.ships as s (s.name)}
                  <li class="shiprow">
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
  {/if}
{/snippet}

<div class="screen">
  {#if loading}
    <p class="msg">Loading games…</p>
  {:else if error}
    <p class="msg err">Couldn't reach the API: {error}</p>
  {:else}
    <div class="cols">
      <section class="games">
        {#if solo?.game}
          <h2>My solo game</h2>
          <ul>
            <li class="solo">
              <!-- Straight into the map: there is nobody else on the standings to look at. -->
              <button type="button" class="pick" onclick={() => onPick(solo.game.name, me.name)}>
                <span class="head">
                  <span class="nm">{solo.game.display}</span>
                  <span class="rnd">Round {solo.game.current_round}</span>
                </span>
                <span class="meta next">no deadline · say you are ready and the round runs</span>
              </button>
              <button type="button" class="corner" onclick={() => onReplay(solo.game.name)}>Replay ›</button>
            </li>
          </ul>
        {/if}

        <h2 class:later={solo?.game}>Games</h2>
        {#if !games.length}
          <p class="msg quiet">
            No games yet. The director will add you to one{#if !solo?.game}, or
            <button type="button" class="link" onclick={() => onPage("solo")}>start a solo game</button>
            of your own{/if}.
          </p>
        {/if}
        <ul>
          {#each games as g (g.name)}
            <li>
              <button type="button" class="pick" class:on={g.name === game}
                      onclick={() => chooseGame(g.name)}>
                <span class="head">
                  <span class="nm">{g.display}</span>
                  <span class="rnd">Round {g.standing.round_nr}</span>
                </span>
                <span class="meta next">
                  {#if g.next_processing}
                    next {whenLocal(g.next_processing)} · <span class="soon">{until(g.next_processing)}</span>
                  {:else}
                    no deadline, the director runs it
                  {/if}
                </span>
                <span class="meta gauge">
                  <span class="lbl">saved</span>
                  <span class="bar"><i style="width: {pct(g.standing.players_saved, g.standing.players)}%"></i></span>
                  <span class="cnt">{g.standing.players_saved}/{g.standing.players}</span>
                </span>
                <span class="meta gauge">
                  <span class="lbl">ready</span>
                  <span class="bar ready"><i style="width: {pct(g.standing.players_ready, g.standing.players)}%"></i></span>
                  <span class="cnt">{g.standing.players_ready}/{g.standing.players}</span>
                </span>
              </button>

              {#if inline && g.name === game}
                <div class="opened">{@render standings()}</div>
              {/if}
            </li>
          {/each}
        </ul>
      </section>

      {#if !inline}
        <section class="detail">
          <h2>{game ? `${game} · planning round ${(overview?.last_round ?? 0) + 1}, best first` : "Factions"}</h2>
          {#if !game}
            <p class="msg quiet">Pick a game first.</p>
          {:else}
            {@render standings()}
          {/if}
        </section>
      {/if}
    </div>
  {/if}
</div>

<style>
  .screen {
    height: 100%; overflow-y: auto; overscroll-behavior: contain; padding: 28px 32px 40px;
    background: radial-gradient(120% 90% at 50% 0%, #0e1526 0%, #080b12 70%);
  }
  .cols { max-width: 1000px; margin-left: auto; margin-right: auto;
          display: flex; gap: 28px; align-items: flex-start; }
  .games { width: 280px; flex-shrink: 0; }
  .detail { flex: 1; min-width: 0; }
  h2 { margin: 0 0 10px; font-size: 11px; font-weight: 600; letter-spacing: 0.16em;
       text-transform: uppercase; color: var(--ink-dim); }
  h2.later { margin-top: 20px; }

  .link { font: inherit; color: var(--cyan); background: transparent; border: none; padding: 0;
          text-decoration: underline; cursor: pointer; }

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
  .head { display: flex; align-items: baseline; gap: 10px; }
  .head .nm { flex: 1; min-width: 0; }
  .rnd { font-size: 11px; color: var(--ink-dim); white-space: nowrap; }
  .meta { font-size: 11px; color: var(--ink-dim); }
  .next { margin-top: 2px; color: var(--ink); }
  .next .soon { color: var(--amber); }

  /* How far the round has got, per commander: what the director's console shows, for the
     people waiting on each other. */
  .gauge { display: flex; align-items: center; gap: 7px; margin-top: 3px; }
  .gauge .lbl { color: var(--ink-faint); }
  .gauge .cnt { font-variant-numeric: tabular-nums; }
  .gauge .bar { flex: 1; height: 3px; background: var(--grid); border-radius: 2px;
                overflow: hidden; }
  .gauge .bar i { display: block; height: 100%; background: var(--ok); }
  .gauge .bar.ready i { background: var(--cyan); }

  /* Standings opened under the game they belong to, when there is no column to put them in. */
  .opened { padding: 12px 0 6px; }

  /* A solo game has no standings for a replay to sit on top of, so it sits in the box itself. */
  .solo { position: relative; }
  .solo .pick { padding-bottom: 34px; }
  .corner {
    position: absolute; right: 7px; bottom: 6px;
    display: inline-flex; align-items: center; min-height: 28px; padding: 0 10px;
    font-family: var(--mono); font-size: 11px; color: var(--ok);
    background: #0d1320; border: 1px solid var(--edge); border-radius: 3px; cursor: pointer;
  }
  .corner:hover { border-color: var(--ok); }
  .corner:focus-visible { outline: 2px solid var(--ok); outline-offset: 1px; }

  .replay {
    display: block; width: 100%; margin-bottom: 14px; padding: 9px 11px;
    font-family: var(--mono); font-size: 12px; text-align: left; color: var(--cyan);
    background: #0d1320; border: 1px solid var(--edge); border-radius: 3px; min-height: 40px;
  }
  .replay:hover { border-color: var(--cyan); }
  .replay:focus-visible { outline: 2px solid var(--cyan); outline-offset: 1px; }

  .faction { --col: 60px; margin-bottom: 18px; }
  .fhead { display: flex; align-items: baseline; gap: 10px; padding: 0 11px 6px;
           border-bottom: 1px solid var(--edge); margin-bottom: 6px; }
  .rank { font-size: 11px; color: var(--ink-faint); font-variant-numeric: tabular-nums;
          min-width: 14px; }
  .fname { font-size: 12.5px; color: var(--hull); font-weight: 600; letter-spacing: 0.06em; }
  .fscore { margin-left: auto; min-width: 40px; text-align: right; font-size: 12.5px;
            color: var(--amber); font-variant-numeric: tabular-nums; }
  .st.head { font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase;
             color: var(--ink-faint); }
  .short { display: none; }

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

  /* A fleet's own ships, indented under its commander. The padding on the right is the two
     status columns, so their scores stay in the column the scores above them are in. */
  .ships { margin: 2px 0 0; padding: 0 calc(2 * var(--col) + 21px) 0 22px; gap: 0; }
  .shiprow { display: flex; align-items: center; gap: 9px; padding: 3px 10px;
             font-size: 11.5px; color: var(--ink-dim); }
  .shiprow .nm { min-width: 120px; color: var(--ink); }
  .shiprow .nm.gone { color: var(--ink-faint); text-decoration: line-through; }
  .shiprow .ty { flex: 1; font-size: 11px; }
  .sc { min-width: 40px; text-align: right; font-variant-numeric: tabular-nums; }

  /* Saved and ready are per commander, not per ship: amber for still owed, since neither is
     late until the deadline. */
  .st { min-width: var(--col); text-align: right; font-size: 11.5px; color: var(--amber);
        flex-shrink: 0; }
  .st.ok { color: var(--ok); }
  .st.out { color: var(--ink-faint); }
  .dot { display: none; }

  .msg { font-size: 13px; color: var(--ink); line-height: 1.6; }
  .msg.err { color: var(--warn); }
  .msg.quiet { color: var(--ink-faint); }

  @media (max-width: 820px) {
    /* Cross axis, once the direction is a column: without this every block is content-wide. */
    .cols { flex-direction: column; align-items: stretch; }
    .games { width: auto; }
  }

  /* A phone has no room for two words per commander per row. The words become a lamp, lit for
     done and hollow for still owed, and the ship type goes: it is on the fleet rows already. */
  @media (max-width: 620px) {
    .screen { padding: 16px 12px 28px; }
    .solo .pick { padding-bottom: 46px; }
    .corner { min-height: 40px; padding: 0 14px; }
    .faction { --col: 18px; }
    .ship { gap: 8px; padding: 8px 10px; }
    .ship .nm { min-width: 0; flex: 1 1 auto; overflow: hidden; text-overflow: ellipsis; }
    .ship .ty { display: none; }
    .ship .pl { min-width: 0; flex: 0 1 auto; overflow: hidden; text-overflow: ellipsis;
                white-space: nowrap; }
    .sc { min-width: 30px; }
    .ships { padding-right: calc(2 * var(--col) + 16px); }
    .shiprow { gap: 8px; }
    .shiprow .nm { min-width: 0; flex: 1 1 auto; }
    .shiprow .ty { display: none; }

    .st { display: flex; justify-content: flex-end; }
    .st .long { display: none; }
    .short { display: inline; }
    .dot { display: block; width: 10px; height: 10px; border-radius: 50%;
           border: 2px solid currentColor; }
    .dot.filled { background: currentColor; }
    .dot.none { opacity: 0.35; border-style: dotted; }
  }
</style>
