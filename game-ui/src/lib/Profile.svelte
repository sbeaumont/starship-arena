<script>
  // Reminders, and nothing else yet. Two ways of being told you still owe orders, asked for
  // separately: a lead time on whatever the game's next deadline is, and an hour of your own day.
  import { untrack } from "svelte";

  let { me, onSaved } = $props();

  // The zone the reminder hour is an hour of. The browser knows it, so nobody is asked to pick
  // one off a list of four hundred, and it is the IANA name rather than an offset because an
  // offset is only right until the clocks go back.
  const here = Intl.DateTimeFormat().resolvedOptions().timeZone;

  // Seeded once and then the form's own: what is typed here must survive `me` coming back from
  // a save. Reading it on purpose rather than tracking it is what `untrack` says.
  const already = untrack(() => me.reminders);

  // Whole hours, because the reminder pass runs hourly: offering minutes would be offering a
  // precision nothing downstream keeps.
  const HOURS = Array.from({ length: 24 }, (_, h) => h);
  const clock = (h) => `${String(h).padStart(2, "0")}:00`;

  let discordId = $state(already.discord_id);
  let ahead = $state(already.hours_before > 0);
  let hours = $state(already.hours_before || 6);
  let daily = $state(already.daily_hour !== null);
  let at = $state(already.daily_hour ?? 8);
  // Their stored zone wins until they save, so opening this on holiday does not silently move it.
  let zone = $state(already.timezone || here);

  let busy = $state(false);
  let error = $state(null);
  let saved = $state(false);

  const reachable = $derived(!!discordId.trim());

  async function save() {
    busy = true;
    error = null;
    saved = false;
    try {
      const res = await fetch("/api/game/me/reminders", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          discord_id: discordId.trim(),
          hours_before: ahead ? Number(hours) : 0,
          daily_hour: daily ? Number(at) : null,
          timezone: daily ? zone : "",
        }),
      });
      const answer = await res.json();
      if (!res.ok) {
        error = answer.detail ?? `API returned ${res.status}`;
        return;
      }
      saved = true;
      onSaved(answer);
    } catch (e) {
      error = String(e);
    } finally {
      busy = false;
    }
  }
</script>

<div class="screen">
  <header><h1>Profile</h1></header>

  <section class="card">
    <h2>Reminders</h2>
    <p class="blurb">
      A nudge in the Discord channel when a round is waiting on you. Nothing is sent unless you
      ask for it here, and nothing is sent at all once your orders are in.
    </p>

    <label class="field">
      <span class="what">Discord user ID</span>
      <input type="text" bind:value={discordId} autocomplete="off" placeholder="690000000000000001" />
    </label>
    <p class="hint">
      In Discord: Settings → Advanced → Developer Mode, then right-click your name → Copy User ID.
      Without it there is nowhere to send anything.
    </p>

    <div class="option" class:off={!reachable}>
      <label class="pick">
        <input type="checkbox" bind:checked={ahead} disabled={!reachable} />
        <span>Before a deadline</span>
      </label>
      <div class="detail">
        <input type="number" min="1" max="72" bind:value={hours} disabled={!ahead || !reachable} />
        <span class="unit">hours ahead of whenever the round closes</span>
      </div>
    </div>

    <div class="option" class:off={!reachable}>
      <label class="pick">
        <input type="checkbox" bind:checked={daily} disabled={!reachable} />
        <span>Once a day</span>
      </label>
      <div class="detail">
        <select bind:value={at} disabled={!daily || !reachable}>
          {#each HOURS as h (h)}
            <option value={h}>{clock(h)}</option>
          {/each}
        </select>
        <span class="unit">on the hour</span>
      </div>
      <p class="zone" class:muted={!daily}>
        <strong>{clock(at)} where you are</strong> — {zone}, not the server's clock.
        {#if zone !== here}
          This browser says {here}.
          <button type="button" class="inline" onclick={() => (zone = here)}>Use it</button>
        {/if}
      </p>
    </div>

    <div class="act">
      <button type="button" disabled={busy} onclick={save}>Save</button>
      {#if saved}<span class="in">Saved.</span>{/if}
    </div>
    {#if error}<p class="err">{error}</p>{/if}
  </section>
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

  .blurb { margin: 6px 0 16px; font-size: 12.5px; line-height: 1.6; color: var(--ink-dim);
           max-width: 70ch; }

  .field { display: flex; align-items: center; gap: 12px; }
  .what { font-size: 12.5px; color: var(--ink-dim); min-width: 130px; }

  input, select {
    font-family: var(--mono); font-size: 12.5px; color: var(--ink);
    background: #080b12; border: 1px solid var(--edge); border-radius: 3px; padding: 7px 10px;
  }
  input[type="text"] { flex: 1; min-width: 160px; }
  input[type="number"] { width: 80px; }
  select { width: 90px; }
  input:focus, select:focus { border-color: var(--cyan); outline: none; }
  input::placeholder { color: var(--ink-faint); }
  input:disabled, select:disabled { opacity: 0.4; }

  /* The one thing a reader has to take from this page: the hour is theirs, not the server's. */
  .zone { margin: 10px 0 0 23px; font-size: 12px; line-height: 1.5; color: var(--ink-dim); }
  .zone strong { color: var(--amber); font-weight: 600; }
  .zone.muted { opacity: 0.45; }

  .hint { margin: 6px 0 0; font-size: 11.5px; line-height: 1.5; color: var(--ink-faint);
          max-width: 70ch; }

  .option { margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--edge); }
  .option.off { opacity: 0.5; }
  .pick { display: flex; align-items: center; gap: 8px; font-size: 12.5px; color: var(--ink); }
  .pick input { width: 15px; height: 15px; accent-color: var(--amber); padding: 0; }
  .detail { display: flex; align-items: center; gap: 10px; margin: 8px 0 0 23px; }
  .unit { font-size: 11.5px; color: var(--ink-faint); }

  .act { display: flex; align-items: center; gap: 10px; margin-top: 20px; }
  button {
    font-family: var(--mono); font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--amber); background: transparent; border: 1px solid var(--edge); border-radius: 3px;
    padding: 6px 12px; cursor: pointer;
  }
  button:hover:not(:disabled) { border-color: var(--amber); }
  button:disabled { opacity: 0.4; cursor: default; }
  button.inline { padding: 2px 6px; font-size: 10px; margin-left: 4px; }

  .in { font-size: 11.5px; color: var(--ok); }
  .err { margin: 10px 0 0; font-size: 12px; color: var(--warn); }

  @media (max-width: 820px) {
    .field { flex-direction: column; align-items: stretch; gap: 6px; }
    .what { min-width: 0; }
  }
</style>