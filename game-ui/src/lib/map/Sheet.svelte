<script>
  // The tables a phone has no room for, on a sheet that pulls up over the map. Three heights:
  // shut, half, and most of the screen. The tab row is always there, so what is underneath is
  // never a surprise.
  let { tabs, open = $bindable(null), children } = $props();

  const DETENTS = [0, 0.45, 0.82];

  let detent = $state(0);
  let vh = $state(window.innerHeight);
  let dragging = $state(null);   // height in px while a finger is on the grip

  $effect(() => {
    const on = () => (vh = window.innerHeight);
    addEventListener("resize", on);
    return () => removeEventListener("resize", on);
  });

  const maxH = $derived(vh * DETENTS[2]);
  const height = $derived(dragging ?? vh * DETENTS[detent]);

  function show(name) {
    if (open === name && detent > 0) { detent = 0; return; }
    open = name;
    if (detent === 0) detent = 1;
  }

  let startY = 0, startH = 0;

  function gripDown(e) {
    startY = e.clientY;
    startH = height;
    dragging = height;
    e.currentTarget.setPointerCapture(e.pointerId);
  }

  function gripMove(e) {
    if (dragging === null) return;
    dragging = Math.max(0, Math.min(maxH, startH + (startY - e.clientY)));
  }

  function gripUp(e) {
    if (dragging === null) return;
    const want = dragging / vh;
    let best = 0;
    for (let i = 1; i < DETENTS.length; i++) {
      if (Math.abs(DETENTS[i] - want) < Math.abs(DETENTS[best] - want)) best = i;
    }
    detent = best;
    if (best > 0 && !open) open = tabs[0].toLowerCase();
    dragging = null;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (_) { /* already gone */ }
  }
</script>

<div class="sheet" style="height: {height}px">
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="grip" onpointerdown={gripDown} onpointermove={gripMove}
       onpointerup={gripUp} onpointercancel={gripUp}>
    <span></span>
  </div>
  <nav>
    {#each tabs as name (name)}
      <button type="button" class:on={open === name.toLowerCase() && detent > 0}
              onclick={() => show(name.toLowerCase())}>{name}</button>
    {/each}
  </nav>
  {#if height > 0}
    <div class="body">{@render children?.()}</div>
  {/if}
</div>

<style>
  .sheet {
    flex-shrink: 0; display: flex; flex-direction: column; overflow: hidden;
    background: var(--panel); border-top: 1px solid var(--edge);
    padding-bottom: env(safe-area-inset-bottom);
  }
  /* The grip is its own row and takes the whole width, because a finger arriving anywhere along
     the top of the sheet means the same thing. */
  .grip { flex-shrink: 0; display: flex; justify-content: center; padding: 8px 0 4px;
          touch-action: none; cursor: ns-resize; }
  .grip span { width: 44px; height: 4px; border-radius: 2px; background: var(--ink-faint); }

  nav { display: flex; flex-shrink: 0; }
  nav button {
    flex: 1; min-height: 40px; font-family: var(--mono); font-size: 11px; letter-spacing: 0.12em;
    text-transform: uppercase; color: var(--ink-dim); background: transparent;
    border: none; border-bottom: 2px solid transparent;
  }
  nav button.on { color: var(--amber); border-bottom-color: var(--amber); }

  .body { flex: 1; min-height: 0; overflow-y: auto; overscroll-behavior: contain;
          padding: 14px 16px 24px; border-top: 1px solid var(--edge); }
</style>
