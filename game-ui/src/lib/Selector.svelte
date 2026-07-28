<script>
  let { onPick } = $props();

  let games = $state([]);
  let players = $state([]);
  let game = $state(null);
  let loading = $state(true);
  let loadingPlayers = $state(false);
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

  async function chooseGame(name) {
    game = name;
    players = [];
    loadingPlayers = true;
    try {
      const res = await fetch(`/api/game/${name}/players`);
      players = await res.json();
    } finally {
      loadingPlayers = false;
    }
  }
</script>

<div class="screen">
  <header>
    <h1>Starship Arena</h1>
    <p class="sub">Choose a game, then whose picture to look at.</p>
  </header>

  {#if loading}
    <p class="msg">Loading games…</p>
  {:else if error}
    <p class="msg err">Couldn't reach the API: {error}<br />Is arena-api.sh running on :8000?</p>
  {:else}
    <div class="cols">
      <section>
        <h2>Game</h2>
        <ul>
          {#each games as g (g.name)}
            <li>
              <button type="button" class:on={g.name === game} onclick={() => chooseGame(g.name)}>
                <span class="nm">{g.name}</span>
                <span class="meta">
                  {g.current_round === 1 ? "not played yet" : `${g.current_round - 1} rounds played`}
                </span>
              </button>
            </li>
          {/each}
        </ul>
      </section>

      <section>
        <h2>Player</h2>
        {#if !game}
          <p class="msg quiet">Pick a game first.</p>
        {:else if loadingPlayers}
          <p class="msg quiet">Loading players…</p>
        {:else if !players.length}
          <p class="msg quiet">No players in {game}.</p>
        {:else}
          <ul>
            {#each players as p (p.name)}
              <li>
                <button type="button" onclick={() => onPick(game, p.name)}>
                  <span class="nm">{p.name}</span>
                  <span class="meta">faction {p.faction} · {p.ships.join(", ")}</span>
                </button>
              </li>
            {/each}
          </ul>
        {/if}
      </section>
    </div>
    <p class="honour">
      There is no login yet: please look only at your own ships while a round is open.
    </p>
  {/if}
</div>

<style>
  .screen {
    height: 100%; overflow-y: auto; padding: 40px 32px;
    background: radial-gradient(120% 90% at 50% 0%, #0e1526 0%, #080b12 70%);
  }
  header { max-width: 900px; margin: 0 auto 28px; }
  h1 { margin: 0; font-size: 19px; font-weight: 600; letter-spacing: 0.2em;
       text-transform: uppercase; color: var(--hull); }
  .sub { margin: 8px 0 0; font-size: 13px; color: var(--ink-dim); }

  .cols { max-width: 900px; margin: 0 auto; display: flex; gap: 28px; align-items: flex-start; }
  section { flex: 1; min-width: 0; }
  h2 { margin: 0 0 10px; font-size: 11px; font-weight: 600; letter-spacing: 0.16em;
       text-transform: uppercase; color: var(--ink-dim); }

  ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
  button {
    width: 100%; display: flex; flex-direction: column; gap: 2px; text-align: left;
    font-family: var(--mono); font-size: 13px; color: var(--ink);
    background: #0d1320; border: 1px solid var(--edge); border-radius: 3px;
    padding: 9px 12px; cursor: pointer; transition: border-color 0.15s, color 0.15s;
  }
  button:hover { border-color: var(--cyan); color: var(--cyan); }
  button.on { border-color: var(--amber); color: var(--amber); }
  button:focus-visible { outline: 2px solid var(--cyan); outline-offset: 1px; }
  .nm { font-weight: 600; }
  .meta { font-size: 11px; color: var(--ink-dim); }

  .msg { font-size: 13px; color: var(--ink); line-height: 1.6; }
  .msg.err { color: var(--warn); }
  .msg.quiet { color: var(--ink-faint); }
  .honour { max-width: 900px; margin: 28px auto 0; font-size: 11.5px; color: var(--ink-faint); }

  @media (max-width: 700px) { .cols { flex-direction: column; } }
</style>