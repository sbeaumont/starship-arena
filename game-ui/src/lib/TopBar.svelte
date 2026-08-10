<script>
  // The chrome every page keeps: who you are, what the server's clock says, and where else you
  // can go. The map is the exception, since it needs the room. Narrow enough and the links fold
  // into a drawer, because six of them across a phone is four too many.
  let { me = null, page = null, directing = false, asPlayer = false, clock = "", zone = "",
        onToggleAsPlayer, onPage, onHome, onSignOut } = $props();

  let open = $state([]);
  let drawer = $state(false);

  $effect(() => {
    if (!me) return;
    (async () => {
      const res = await fetch("/api/game/open");
      if (res.ok) open = await res.json();
    })();
  });

  // Going somewhere always shuts the drawer, so nothing has to remember to.
  function shut(then) {
    drawer = false;
    then();
  }
</script>

<header>
  <div class="row">
    <button type="button" class="burger" onclick={() => (drawer = true)} aria-label="Menu">
      <span></span><span></span><span></span>
    </button>
    <button type="button" class="brand" onclick={() => shut(onHome)}>Starship Arena</button>
    {#if me}
      <p class="sub">
        Signed in as {me.name}{#if me.is_director} · <span class="role">{directing ? "director" : "director, looking as a player"}</span>{/if}
        {#if clock} · <span class="clock">server time {clock} {zone}</span>{/if}
      </p>
    {/if}
  </div>

  <nav class:open={drawer}>
    {#if me}
      <button type="button" class:here={!page} onclick={() => shut(onHome)}>Games</button>
      <button type="button" class:here={page === "solo"} onclick={() => shut(() => onPage("solo"))}>Solo</button>
      <button type="button" class:here={page === "register"} onclick={() => shut(() => onPage("register"))}>
        {open.length ? `Register (${open.length})` : "Register"}
      </button>
    {/if}
    <button type="button" class:here={page === "ships"} onclick={() => shut(() => onPage("ships"))}>Ships</button>
    <button type="button" class:here={page === "lore"} onclick={() => shut(() => onPage("lore"))}>Lore</button>
    <button type="button" onclick={() => shut(() => window.open("/api/game/manual", "_blank"))}>Manual</button>
    {#if me}
      <button type="button" onclick={() => shut(onSignOut)}>Sign out</button>
    {:else}
      <button type="button" onclick={() => shut(onHome)}>Sign in</button>
    {/if}

    <span class="right">
      {#if me?.is_director}
        <button type="button" class="mode" class:on={asPlayer} onclick={() => shut(onToggleAsPlayer)}>
          {asPlayer ? "View as director" : "View as player"}
        </button>
      {/if}
      {#if directing && me.admin_url}
        <a href={me.admin_url}>Console</a>
      {/if}
    </span>
  </nav>
</header>

{#if drawer}
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <div class="scrim" onclick={() => (drawer = false)}></div>
{/if}

<style>
  header { flex-shrink: 0; padding: 14px 32px 12px; background: #0a0f1a;
           border-bottom: 1px solid var(--edge); padding-top: max(14px, env(safe-area-inset-top)); }
  .row { display: flex; align-items: baseline; gap: 24px; }
  .row, nav { max-width: 1000px; margin-left: auto; margin-right: auto; }

  .burger { display: none; }

  .brand {
    font-family: var(--mono); font-size: 15px; font-weight: 600; letter-spacing: 0.2em;
    text-transform: uppercase; color: var(--hull); background: transparent; border: none;
    padding: 0; cursor: pointer;
  }
  .brand:hover { color: var(--cyan); }

  nav { display: flex; align-items: baseline; gap: 16px; margin-top: 10px; }
  nav button, nav a {
    font-family: var(--mono); font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--ink-dim); background: transparent; border: none;
    border-bottom: 1px solid var(--edge); padding: 0 0 2px; cursor: pointer;
    text-decoration: none;
  }
  nav button:hover, nav a:hover { color: var(--cyan); border-color: var(--cyan); }
  /* Amber is where you are, and nothing else, or a tab that merely has news reads as selected. */
  nav button.here { color: var(--amber); border-color: var(--amber); }
  .right { display: flex; align-items: baseline; gap: 16px; margin-left: auto; }

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

  .scrim { position: fixed; inset: 0; background: rgba(4, 7, 13, 0.65); z-index: 20; }

  /* Narrow: the links leave the header for a drawer, and the row keeps only the brand. */
  @media (max-width: 720px) {
    header { padding: 8px 12px; padding-top: max(8px, env(safe-area-inset-top)); }
    .row { align-items: center; gap: 10px; }
    .burger {
      display: flex; flex-direction: column; justify-content: center; gap: 4px;
      width: 40px; height: 40px; padding: 0 9px; flex-shrink: 0;
      background: transparent; border: none; cursor: pointer;
    }
    .burger span { display: block; height: 2px; background: var(--ink); border-radius: 1px; }
    .brand { font-size: 13px; letter-spacing: 0.14em; }
    .sub { display: none; }

    nav {
      position: fixed; top: 0; left: 0; bottom: 0; width: min(300px, 82vw); z-index: 21;
      display: none; flex-direction: column; align-items: stretch; gap: 0; margin: 0;
      background: var(--panel); border-right: 1px solid var(--edge); overflow-y: auto;
      padding: max(16px, env(safe-area-inset-top)) 0 env(safe-area-inset-bottom);
    }
    nav.open { display: flex; animation: slide 0.16s ease-out; }
    nav button, nav a {
      display: flex; align-items: center; min-height: 50px; padding: 0 18px;
      font-size: 13px; border-bottom: 1px solid var(--edge); text-align: left;
    }
    nav button.here { background: #16203a; }
    .right { flex-direction: column; align-items: stretch; gap: 0; margin-left: 0; }
    .mode { margin: 14px 18px; min-height: 44px; border-radius: 4px; }
  }
  @keyframes slide { from { transform: translateX(-100%); } to { transform: none; } }
</style>
