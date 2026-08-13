<script>
  // The games that are over, open to anybody. Nothing here asks who is reading: a finished game
  // has nobody left to keep anything from, which is what lets this page be the front door for
  // somebody who has never played.
  let { onOpen } = $props();

  let games = $state([]);
  let loading = $state(true);
  let error = $state(null);

  $effect(() => {
    (async () => {
      try {
        const res = await fetch("/api/game/valhalla");
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        games = await res.json();
      } catch (e) {
        error = String(e);
      } finally {
        loading = false;
      }
    })();
  });
</script>

<div class="screen">
  <div class="inner">
    <h1>Valhalla</h1>
    <p class="lede">
      Wars that are over, kept as they were fought. Watch one from any side, or from all of them
      at once — nothing is hidden from you here.
    </p>

    {#if loading}
      <p class="msg">Loading…</p>
    {:else if error}
      <p class="msg err">Couldn't reach the API: {error}</p>
    {:else if !games.length}
      <p class="msg quiet">Nothing has been laid to rest yet.</p>
    {:else}
      <ul>
        {#each games as g (g.name)}
          <li>
            <button type="button" class="pick" onclick={() => onOpen(g.name)}>
              <span class="head">
                <span class="nm">{g.display}</span>
                <span class="rnd">{g.rounds} rounds</span>
              </span>
              <span class="meta">{g.factions.length} sides · {g.factions.join(", ")}</span>
              <span class="meta who">{g.players.join(", ")}</span>
            </button>
          </li>
        {/each}
      </ul>
    {/if}
  </div>
</div>

<style>
  .screen {
    height: 100%; overflow-y: auto; overscroll-behavior: contain; padding: 28px 32px 40px;
    background: radial-gradient(120% 90% at 50% 0%, #0e1526 0%, #080b12 70%);
  }
  .inner { max-width: 640px; margin: 0 auto; }
  h1 { margin: 0 0 8px; font-size: 15px; font-weight: 600; letter-spacing: 0.16em;
       text-transform: uppercase; color: var(--hull); }
  .lede { margin: 0 0 22px; font-size: 13px; line-height: 1.6; color: var(--ink-dim); }

  ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 3px; }
  .pick {
    width: 100%; display: flex; flex-direction: column; gap: 2px; text-align: left;
    font-family: var(--mono); font-size: 13px; color: var(--ink);
    background: #0d1320; border: 1px solid var(--edge); border-radius: 3px;
    padding: 10px 12px; min-height: 44px; cursor: pointer; transition: border-color 0.15s, color 0.15s;
  }
  .pick:hover { border-color: var(--cyan); color: var(--cyan); }
  .pick:focus-visible { outline: 2px solid var(--cyan); outline-offset: 1px; }
  .head { display: flex; align-items: baseline; gap: 10px; }
  .head .nm { flex: 1; min-width: 0; }
  .rnd { font-size: 11px; color: var(--ink-dim); white-space: nowrap; }
  .meta { font-size: 11px; color: var(--ink-dim); margin-top: 2px; }
  .who { color: var(--ink-faint); }

  .msg { font-size: 13px; color: var(--ink); line-height: 1.6; }
  .msg.err { color: var(--warn); }
  .msg.quiet { color: var(--ink-faint); }

  @media (max-width: 620px) {
    .screen { padding: 16px 12px 28px; }
  }
</style>