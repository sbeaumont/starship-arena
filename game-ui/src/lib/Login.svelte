<script>
  let { onLoggedIn, onPage, message } = $props();

  let name = $state("");
  let problem = $state(null);
  let sending = $state(false);

  async function register(e) {
    e.preventDefault();
    problem = null;
    sending = true;
    try {
      const res = await fetch("/api/game/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim() }),
      });
      const body = await res.json();
      if (res.ok) onLoggedIn(body);
      else problem = body.detail ?? `API returned ${res.status}`;
    } catch (err) {
      problem = String(err);
    } finally {
      sending = false;
    }
  }
</script>

<div class="screen">
  <div class="card">
    <h1>Starship Arena</h1>

    {#if message}
      <p class="warn">{message}</p>
    {/if}

    <p>
      Every commander has their own link. Open the one the director sent you and this machine
      stays signed in.
    </p>

    <form onsubmit={register}>
      <h2>New here?</h2>
      <p class="sub">Claim the name you want to be known by, in this game and every one after
        it. The director assigns you ships once you have a name.</p>
      <div class="row">
        <input type="text" bind:value={name} placeholder="Your commander name"
               autocomplete="off" spellcheck="false" />
        <button type="submit" disabled={sending || !name.trim()}>Claim</button>
      </div>
      {#if problem}<p class="err">{problem}</p>{/if}
    </form>

    <p class="sub">
      Already commanding ships and no link? Ask the director to send you one — your name is
      already taken, by you.
    </p>

    <nav>
      <button type="button" onclick={() => onPage("ships")}>Ships</button>
      <button type="button" onclick={() => onPage("lore")}>Lore</button>
    </nav>
  </div>
</div>

<style>
  .screen {
    height: 100%; overflow-y: auto; display: flex; align-items: center; justify-content: center;
    padding: 40px 24px;
    background: radial-gradient(120% 90% at 50% 0%, #0e1526 0%, #080b12 70%);
  }
  .card { width: 100%; max-width: 460px; }
  h1 { margin: 0 0 22px; font-size: 19px; font-weight: 600; letter-spacing: 0.2em;
       text-transform: uppercase; color: var(--hull); }
  h2 { margin: 0 0 6px; font-size: 11px; font-weight: 600; letter-spacing: 0.16em;
       text-transform: uppercase; color: var(--ink-dim); }
  p { margin: 0 0 18px; font-size: 13px; line-height: 1.6; color: var(--ink); }
  .sub { color: var(--ink-dim); font-size: 12px; }
  .warn { color: var(--amber); border-left: 2px solid var(--amber); padding-left: 10px; }
  .err { color: var(--warn); font-size: 12px; margin: 8px 0 0; }

  form { border-top: 1px solid var(--edge); padding-top: 20px; margin-bottom: 20px; }
  .row { display: flex; gap: 8px; }
  input {
    flex: 1; font-family: var(--mono); font-size: 13px; color: var(--ink);
    background: #0d1320; border: 1px solid var(--edge); border-radius: 3px; padding: 8px 10px;
  }
  input:focus { outline: none; border-color: var(--cyan); }
  button[type=submit] {
    font-family: var(--mono); font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--amber); background: transparent; border: 1px solid var(--amber);
    border-radius: 3px; padding: 8px 14px; cursor: pointer;
  }
  button[type=submit]:hover:not(:disabled) { background: var(--amber); color: #14100a; }
  button[type=submit]:disabled { opacity: 0.35; cursor: not-allowed; }

  nav { display: flex; gap: 16px; border-top: 1px solid var(--edge); padding-top: 16px; }
  nav button {
    font-family: var(--mono); font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--ink-dim); background: transparent; border: none; padding: 0; cursor: pointer;
  }
  nav button:hover { color: var(--cyan); }
</style>