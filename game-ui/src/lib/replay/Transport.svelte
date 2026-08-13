<script>
  // The controls under a replay: where you are, and how you get somewhere else. Every target is a
  // fingertip wide, since this is one implementation for both.
  //
  // Nothing else. This bar is the one thing always on a phone's screen, so how much trail is
  // drawn and how fast it runs sit in the log panel with the other question about how a tick is
  // shown, rather than taking a row here that a thumb never presses twice.
  let { ph } = $props();
</script>

<div class="transport">
  <div class="keys">
    <button type="button" onclick={() => ph.toStart()} title="Back to the start of the game"
            disabled={ph.at <= ph.first}>❙◀◀</button>
    <button type="button" onclick={() => ph.toRoundStart()} title="Back to the start of the round"
            disabled={ph.at <= ph.first}>◀◀</button>
    <button type="button" onclick={() => ph.step(-1)} title="A tick back"
            disabled={ph.at <= ph.first}>◀❙</button>
    <button type="button" class="play" class:on={ph.playing} onclick={() => ph.toggle()}
            title={ph.playing ? "Pause" : "Play"}>{ph.playing ? "❙❙" : "▶"}</button>
    <button type="button" onclick={() => ph.step(1)} title="A tick on"
            disabled={ph.atEnd}>❙▶</button>
    <button type="button" onclick={() => ph.toRoundEnd()} title="On to the end of the round"
            disabled={ph.atEnd}>▶▶</button>
    <button type="button" onclick={() => ph.toEnd()} title="On to the latest tick"
            disabled={ph.atEnd}>▶▶❙</button>
  </div>

  <span class="where">round <b>{ph.round}</b> · tick <b>{ph.tick}</b></span>

  <input class="scrub" type="range" min={ph.first} max={ph.last} value={ph.at}
         aria-label="Which tick"
         oninput={(e) => { ph.playing = false; ph.goTo(Number(e.currentTarget.value)); }} />
</div>

<style>
  .transport {
    display: flex; align-items: center; flex-wrap: wrap; gap: 10px 14px;
    padding: 10px 14px; border-top: 1px solid var(--edge); background: var(--panel);
  }
  .keys { display: flex; gap: 4px; }
  button {
    min-width: 44px; min-height: 40px; padding: 0 8px;
    font-family: var(--mono); font-size: 12px; color: var(--ink);
    background: #0d1320; border: 1px solid var(--edge); border-radius: 3px;
  }
  button:hover:not(:disabled) { border-color: var(--cyan); color: var(--cyan); }
  button:disabled { opacity: 0.3; cursor: not-allowed; }
  button:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }
  .play.on { color: var(--amber); border-color: var(--amber); }

  .where { font-size: 12px; color: var(--ink-dim); font-variant-numeric: tabular-nums;
           white-space: nowrap; }
  .where b { color: var(--amber); }

  /* The scrub takes whatever is left, and drops to a full row of its own when there is not
     enough of it to drag. */
  .scrub { flex: 1 1 220px; min-width: 160px; accent-color: var(--amber); height: 40px; }

  /* Two rows on a phone, and no more: the keys across the top, the scrub under them. Anything
     that wrapped a third time would be a third of the screen the map is not getting. */
  @media (max-width: 760px) {
    .transport { gap: 8px 10px; padding: 8px 10px max(8px, env(safe-area-inset-bottom)); }
    .keys { flex: 1 1 100%; justify-content: space-between; gap: 0; }
    button { min-width: 42px; }
    .scrub { flex: 1 1 100%; }
    /* The drawer's handle sits directly above and says the same thing, where there is room for it. */
    .where { display: none; }
  }
</style>