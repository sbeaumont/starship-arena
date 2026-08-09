<script>
  // The chrome every page keeps: who you are, what the server's clock says, and where else
  // you can go. The map is the exception, since it needs the room.
  let { me = null, directing = false, asPlayer = false, clock = "", zone = "",
        onToggleAsPlayer, onPage, onHome, onSignOut } = $props();

  let open = $state([]);

  $effect(() => {
    if (!me) return;
    (async () => {
      const res = await fetch("/api/game/open");
      if (res.ok) open = await res.json();
    })();
  });
</script>

<header>
  <div class="row">
    <button type="button" class="brand" onclick={onHome}>Starship Arena</button>
    {#if me}
      <p class="sub">
        Signed in as {me.name}{#if me.is_director} · <span class="role">{directing ? "director" : "director, looking as a player"}</span>{/if}
        {#if me.is_director}
          <button type="button" class="mode" class:on={asPlayer} onclick={onToggleAsPlayer}>
            {asPlayer ? "View as director" : "View as player"}
          </button>
        {/if}
        {#if clock} · <span class="clock">server time {clock} {zone}</span>{/if}
      </p>
    {/if}
  </div>

  <nav>
    {#if me}
      {#if directing && me.admin_url}
        <a href={me.admin_url}>Console</a>
      {/if}
      <button type="button" class:hot={open.length} onclick={() => onPage("register")}>
        {open.length ? `Register (${open.length})` : "Register"}
      </button>
    {/if}
    <button type="button" onclick={() => onPage("ships")}>Ships</button>
    <button type="button" onclick={() => onPage("lore")}>Lore</button>
    <button type="button" onclick={() => window.open("/api/game/manual", "_blank")}>Manual</button>
    {#if me}
      <button type="button" onclick={onSignOut}>Sign out</button>
    {:else}
      <button type="button" onclick={onHome}>Sign in</button>
    {/if}
  </nav>
</header>

<style>
  header { flex-shrink: 0; padding: 14px 32px 12px; background: #0a0f1a;
           border-bottom: 1px solid var(--edge); }
  .row { display: flex; align-items: baseline; gap: 24px; }
  .row, nav { max-width: 1000px; margin-left: auto; margin-right: auto; }

  .brand {
    font-family: var(--mono); font-size: 15px; font-weight: 600; letter-spacing: 0.2em;
    text-transform: uppercase; color: var(--hull); background: transparent; border: none;
    padding: 0; cursor: pointer;
  }
  .brand:hover { color: var(--cyan); }

  nav { display: flex; gap: 16px; margin-top: 10px; }
  nav button, nav a {
    font-family: var(--mono); font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--ink-dim); background: transparent; border: none;
    border-bottom: 1px solid var(--edge); padding: 0 0 2px; cursor: pointer;
    text-decoration: none;
  }
  nav button:hover, nav a:hover { color: var(--cyan); border-color: var(--cyan); }
  nav button.hot { color: var(--amber); }

  .sub { margin: 0 0 0 auto; font-size: 13px; color: var(--ink-dim); }
  .role { color: var(--amber); }
  .clock { color: var(--ink-dim); }

  .mode {
    font-family: var(--mono); font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--amber); background: transparent; border: 1px solid var(--edge); border-radius: 3px;
    padding: 2px 8px; margin-left: 8px; cursor: pointer;
  }
  .mode:hover { border-color: var(--amber); }
  .mode.on { border-color: var(--amber); }
</style>