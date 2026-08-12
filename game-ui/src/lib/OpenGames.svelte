<script>
  let games = $state([]);
  let names = $state({});
  let errors = $state({});
  let busy = $state(null);

  // Every ship a scenario allows gets a box. Leave one blank and you asked for fewer ships;
  // that is less to explain than a button that adds a row.
  function boxes(game) {
    return Array.from({ length: game.max_ships }, (_, i) => game.my_ships[i] ?? "");
  }

  async function load() {
    const res = await fetch("/api/game/open");
    if (!res.ok) return;
    games = await res.json();
    names = Object.fromEntries(games.map((g) => [g.name, boxes(g)]));
  }

  $effect(() => {
    load();
  });

  async function send(game, method, body) {
    busy = game.name;
    errors = { ...errors, [game.name]: null };
    try {
      const res = await fetch(`/api/game/open/${game.name}`, {
        method,
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined,
      });
      const answer = await res.json();
      if (!res.ok) {
        errors = { ...errors, [game.name]: answer.detail ?? `API returned ${res.status}` };
        return;
      }
      games = games.map((g) => (g.name === answer.name ? answer : g));
      names = { ...names, [answer.name]: boxes(answer) };
    } catch (e) {
      errors = { ...errors, [game.name]: String(e) };
    } finally {
      busy = null;
    }
  }

  const asked = (game) => names[game.name]?.filter((n) => n.trim()).length ?? 0;
</script>

<div class="screen">
  <header>
    <h1>Register</h1>
  </header>

  <section class="open">
    {#if !games.length}
      <p class="none">No game is taking registrations right now. The director opens one when the
        next war is being set up.</p>
    {/if}
    {#each games as g (g.name)}
      <div class="card">
        <div class="head">
          <span class="nm">{g.display}</span>
          <span class="sc">{g.scenario}</span>
          <span class="count">{g.players} registered</span>
        </div>
        <p class="blurb">{g.blurb}</p>

        <div class="ships">
          {#each names[g.name] ?? [] as _, i}
            <input
              type="text"
              bind:value={names[g.name][i]}
              placeholder={i === 0 ? "Your ship's name" : "Another ship, if you want one"}
              autocomplete="off"
            />
          {/each}
        </div>

        <div class="act">
          <button type="button" disabled={busy === g.name || !asked(g)} onclick={() => send(g, "PUT", { names: names[g.name] })}>
            {g.my_ships.length ? "Update" : "Register"}
          </button>
          {#if g.my_ships.length}
            <button type="button" class="quiet" disabled={busy === g.name} onclick={() => send(g, "DELETE", null)}>
              Withdraw
            </button>
            <span class="in">You are in, with {g.my_ships.length} {g.my_ships.length === 1 ? "ship" : "ships"}.</span>
          {:else}
            <span class="hint">Up to {g.max_ships}. You may not get them all: the factions are levelled.</span>
          {/if}
        </div>

        {#if errors[g.name]}<p class="err">{errors[g.name]}</p>{/if}
      </div>
    {/each}
  </section>
</div>

<style>
  .screen {
    height: 100%; overflow-y: auto; padding: 40px 32px;
    background: radial-gradient(120% 90% at 50% 0%, #0e1526 0%, #080b12 70%);
  }
  header, .open { max-width: 1000px; margin-left: auto; margin-right: auto; }
  header { margin-bottom: 24px; }
  h1 { margin: 10px 0 0; font-size: 19px; font-weight: 600; letter-spacing: 0.2em;
       text-transform: uppercase; color: var(--hull); }

  .none { margin: 0; font-size: 13px; line-height: 1.6; color: var(--ink-faint); max-width: 70ch; }

  .card { background: #0d1320; border: 1px solid var(--edge); border-radius: 3px;
          padding: 14px 16px; margin-bottom: 8px; }

  .head { display: flex; align-items: baseline; gap: 12px; }
  .nm { font-family: var(--mono); font-size: 13px; color: var(--amber); }
  .sc { font-size: 12.5px; color: var(--hull); }
  .count { margin-left: auto; font-size: 11px; color: var(--ink-faint); }

  .blurb { margin: 6px 0 12px; font-size: 12.5px; line-height: 1.6; color: var(--ink-dim);
           max-width: 70ch; }

  .ships { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
  input {
    flex: 1; min-width: 160px; font-family: var(--mono); font-size: 12.5px; color: var(--ink);
    background: #080b12; border: 1px solid var(--edge); border-radius: 3px; padding: 7px 10px;
  }
  input:focus { border-color: var(--cyan); outline: none; }
  input::placeholder { color: var(--ink-faint); }

  .act { display: flex; align-items: center; gap: 10px; }
  button {
    font-family: var(--mono); font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--amber); background: transparent; border: 1px solid var(--edge); border-radius: 3px;
    padding: 6px 12px; cursor: pointer;
  }
  button:hover:not(:disabled) { border-color: var(--amber); }
  button:disabled { opacity: 0.4; cursor: default; }
  button.quiet { color: var(--ink-dim); }
  button.quiet:hover:not(:disabled) { border-color: var(--warn); color: var(--warn); }

  .hint, .in { font-size: 11.5px; color: var(--ink-faint); }
  .in { color: var(--ok); }
  .err { margin: 10px 0 0; font-size: 12px; color: var(--warn); }

  @media (max-width: 820px) {
    .ships { flex-direction: column; }
  }
</style>