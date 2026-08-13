<script>
  // A game of your own, so there is something to fly before a shared one is being set up. Its
  // own page rather than a row on the games list: you set it up once and then you play it.
  let { onOpen } = $props();

  let solo = $state(null);
  let types = $state([]);
  let rows = $state([]);
  let busy = $state(false);
  let error = $state(null);

  $effect(() => {
    (async () => {
      const [mine, fleet] = await Promise.all([
        fetch("/api/game/solo"),
        fetch("/api/game/ship-types"),
      ]);
      if (fleet.ok) types = (await fleet.json()).filter((t) => t.category === "Ship");
      if (mine.ok) solo = await mine.json();
      // A box per ship the scenario allows. Leave one blank and you asked for fewer, the same
      // way registering for a shared game works.
      rows = Array.from({ length: solo?.max_ships ?? 0 },
                        () => ({ name: "", type: types[0]?.type_name ?? "" }));
    })();
  });

  const asked = $derived(rows.filter((r) => r.name.trim()).length);

  async function start() {
    busy = true;
    error = null;
    try {
      const ships = rows
        .filter((r) => r.name.trim())
        .map((r) => ({ name: r.name.trim(), type: r.type }));
      const res = await fetch("/api/game/solo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ships }),
      });
      const answer = await res.json();
      if (!res.ok) {
        error = answer.detail ?? `API returned ${res.status}`;
        return;
      }
      solo = answer;
      onOpen(answer.game.name);
    } catch (e) {
      error = String(e);
    } finally {
      busy = false;
    }
  }
</script>

<div class="screen">
  <header>
    <h1>Solo</h1>
  </header>

  {#if solo}
    <section class="card">
      <div class="head">
        <span class="sc">{solo.scenario}</span>
        {#if solo.game}
          <span class="count">round {solo.game.current_round}</span>
        {/if}
      </div>
      <p class="blurb">{solo.blurb}</p>

      {#if solo.game}
        <div class="act">
          <button type="button" class="go" onclick={() => onOpen(solo.game.name)}>Continue</button>
          <span class="in">Your game is waiting on round {solo.game.current_round}.</span>
        </div>
      {/if}
    </section>

    <section class="card">
      <h2>{solo.game ? "Start again" : "Start"}</h2>
      {#if solo.game}
        <p class="warn">This throws away the game you have and deals three new pirates.</p>
      {/if}

      <div class="ships">
        {#each rows as row, i}
          <div class="row">
            <input type="text" bind:value={row.name} autocomplete="off"
                   placeholder={i === 0 ? "Your ship's name" : "A second ship, if you want one"} />
            <select bind:value={row.type}>
              {#each types as t (t.type_name)}
                <option value={t.type_name}>{t.name}</option>
              {/each}
            </select>
          </div>
        {/each}
      </div>

      <div class="act">
        <button type="button" disabled={busy || !asked} onclick={start}>
          {solo.game ? "Start again" : "Start"}
        </button>
        <span class="hint">The Ships page says what each hull can do.</span>
      </div>

      {#if error}<p class="err">{error}</p>{/if}
    </section>
  {/if}
</div>

<style>
  .screen {
    height: 100%; overflow-y: auto; padding: 40px 32px;
    background: radial-gradient(120% 90% at 50% 0%, #0e1526 0%, #080b12 70%);
  }
  header, .card { max-width: 1000px; margin-left: auto; margin-right: auto; }
  header { margin-bottom: 24px; }
  h1 { margin: 10px 0 0; font-size: 19px; font-weight: 600; letter-spacing: 0.2em;
       text-transform: uppercase; color: var(--hull); }
  h2 { margin: 0 0 10px; font-size: 11px; font-weight: 600; letter-spacing: 0.16em;
       text-transform: uppercase; color: var(--ink-dim); }

  .card { background: #0d1320; border: 1px solid var(--edge); border-radius: 3px;
          padding: 14px 16px; margin-bottom: 8px; }

  .head { display: flex; align-items: baseline; gap: 12px; }
  .sc { font-size: 12.5px; color: var(--hull); }
  .count { margin-left: auto; font-size: 11px; color: var(--ink-faint); }

  .blurb { margin: 6px 0 12px; font-size: 12.5px; line-height: 1.6; color: var(--ink-dim);
           max-width: 70ch; }
  .warn { margin: 0 0 12px; font-size: 12px; color: var(--amber); }

  .ships { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
  .row { display: flex; gap: 8px; }
  input, select {
    font-family: var(--mono); font-size: 12.5px; color: var(--ink);
    background: #080b12; border: 1px solid var(--edge); border-radius: 3px; padding: 7px 10px;
  }
  input { flex: 1; min-width: 160px; }
  select { flex: 1; min-width: 180px; }
  input:focus, select:focus { border-color: var(--cyan); outline: none; }
  input::placeholder { color: var(--ink-faint); }

  .act { display: flex; align-items: center; gap: 10px; }
  button {
    font-family: var(--mono); font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--amber); background: transparent; border: 1px solid var(--edge); border-radius: 3px;
    padding: 6px 12px; cursor: pointer;
  }
  button:hover:not(:disabled) { border-color: var(--amber); }
  button:disabled { opacity: 0.4; cursor: default; }
  button.go { color: var(--cyan); }
  button.go:hover { border-color: var(--cyan); }

  .hint, .in { font-size: 11.5px; color: var(--ink-faint); }
  .in { color: var(--ok); }
  .err { margin: 10px 0 0; font-size: 12px; color: var(--warn); }

  @media (max-width: 820px) {
    .row { flex-direction: column; }
  }
</style>