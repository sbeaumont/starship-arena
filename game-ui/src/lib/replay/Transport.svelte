<script>
  // The controls under a replay: where you are, how you get somewhere else, and how much trail
  // is drawn. Every target is a fingertip wide, since this is one implementation for both.
  let { ph } = $props();

  const TAILS = [1, 3, 10];
  const SPEEDS = [1, 3, 6];
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

  <label>
    tail
    <select value={ph.tail} onchange={(e) => (ph.tail = Number(e.currentTarget.value))}>
      {#each TAILS as t (t)}<option value={t}>{t === 10 ? "a round" : `${t} tick${t === 1 ? "" : "s"}`}</option>{/each}
    </select>
  </label>

  <label>
    speed
    <select value={ph.perSecond} onchange={(e) => (ph.perSecond = Number(e.currentTarget.value))}>
      {#each SPEEDS as s (s)}<option value={s}>{s}/s</option>{/each}
    </select>
  </label>
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

  label { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--ink-dim); }
  select {
    font: inherit; font-size: 12px; color: var(--ink); background: #0d1320;
    border: 1px solid var(--edge); border-radius: 3px; padding: 6px 4px; min-height: 36px;
  }
</style>