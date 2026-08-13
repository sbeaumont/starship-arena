<script>
  // The games that are over, open to anybody. Reading asks nobody who they are: a game that is
  // over has nobody left to keep anything from, which is what lets this page be the front door
  // for somebody who has never played. Writing is the exception, and it is signed: a commander
  // tells the story of a game they were in, under their own name.
  import { render } from './markdown.js'

  let { me, onOpen } = $props();

  let games = $state([]);
  let loading = $state(true);
  let error = $state(null);

  let opened = $state([]);       // the games whose accounts are folded out, by name
  let writing = $state(null);    // {game, which}: whose entry is being written, and which piece
  let draft = $state('');
  let saving = $state(false);
  let saveError = $state(null);

  const told = (g) => g.stories.length + (g.win_story ? 1 : 0);
  const isOpen = (g) => opened.includes(g.name);
  const fold = (g) =>
    (opened = isOpen(g) ? opened.filter((n) => n !== g.name) : [...opened, g.name]);

  const myStory = (g) => g.stories.find((s) => s.player === me?.name);
  const iFlewIn = (g) =>
    !!me && g.sides.some((s) => s.commanders.some((c) => c.name === me.name));
  // The standing is best first, so the side that took the game is the one at the top of it.
  const iTookIt = (g) =>
    !!me && g.sides.length > 0 && g.sides[0].commanders.some((c) => c.name === me.name);

  function write(g, which, had) {
    if (!isOpen(g)) fold(g);       // so what they write lands where they can see it
    writing = { game: g.name, which };
    draft = had ?? '';
    saveError = null;
  }

  async function save(g) {
    saving = true;
    saveError = null;
    try {
      const res = await fetch(`/api/game/valhalla/${g.name}/${writing.which}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: draft }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail ?? `API returned ${res.status}`);
      games = games.map((known) => (known.name === body.name ? body : known));
      writing = null;
    } catch (e) {
      saveError = String(e);
    } finally {
      saving = false;
    }
  }

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

<!-- One account of a game: the winning side's or one commander's, read and written in the same
     box. `mine` is whether this one is the reader's to change. -->
{#snippet account(g, which, heading, text, mine)}
  <div class="story">
    <h2>{heading}</h2>
    {#if writing?.game === g.name && writing.which === which}
      <textarea bind:value={draft} rows="10"
                placeholder={which === 'win-story'
                  ? `How ${g.sides[0].faction} took it. Anyone who flew for them can write over it.`
                  : 'How it went, from where you were sitting.'}></textarea>
      <p class="hint"># heading, **bold**, *italic*, - bullets, and a blank line between
        paragraphs. Saving nothing takes it down.</p>
      {#if saveError}<p class="err">{saveError}</p>{/if}
      <div class="act">
        <button type="button" onclick={() => { writing = null; saveError = null }}>Cancel</button>
        <button type="button" class="go" disabled={saving}
                onclick={() => save(g)}>{saving ? 'Saving' : 'Save'}</button>
      </div>
    {:else}
      {#if text}
        <div class="prose">{@html render(text)}</div>
      {:else}
        <p class="none">Nothing written yet.</p>
      {/if}
      {#if mine}
        <div class="act">
          <button type="button" onclick={() => write(g, which, text)}>Edit</button>
        </div>
      {/if}
    {/if}
  </div>
{/snippet}

<div class="screen">
  <div class="inner">
    <h1>Valhalla</h1>
    <p class="lede">
      Games that are over, kept as they were played. Watch one from any side, or from all of them
      at once: nothing is hidden from you here.
    </p>

    {#if loading}
      <p class="msg">Loading…</p>
    {:else if error}
      <p class="msg err">Couldn't reach the API: {error}</p>
    {:else if !games.length}
      <p class="msg quiet">Nothing has been laid to rest yet.</p>
    {:else}
      {#each games as g (g.name)}
        <section class="card">
          <div class="head">
            <span class="nm">{g.display}</span>
            <span class="rnd">{g.rounds} rounds</span>
          </div>

          <!-- The final standing, best side first. A side with nobody under it was flown by the
               scenario, and it still earned what it earned. -->
          {#each g.sides as s (s.faction)}
            <div class="side">
              <span class="fname">{s.faction}</span>
              <span class="fscore">{s.score}</span>
              <span class="crew">
                {s.commanders.map((c) => `${c.name} (${c.score})`).join(", ")}
              </span>
            </div>
          {/each}

          {#if g.synopsis}
            <div class="prose">{@html render(g.synopsis)}</div>
          {/if}

          <div class="act">
            {#if told(g) || iFlewIn(g)}
              <button type="button" aria-expanded={isOpen(g)} onclick={() => fold(g)}>
                {isOpen(g) ? 'Hide the stories' : told(g) ? `Stories (${told(g)})` : 'Stories'}
              </button>
            {/if}
            <button type="button" class="go replay" onclick={() => onOpen(g.name)}>Replay</button>
          </div>

          {#if isOpen(g)}
            {#if g.win_story || iTookIt(g)}
              {@render account(g, 'win-story',
                               g.win_story ? `How ${g.win_story.faction} took it · ${g.win_story.player}`
                                           : `How ${g.sides[0].faction} took it`,
                               g.win_story?.text, iTookIt(g))}
            {/if}
            {#each g.stories as s (s.player)}
              {@render account(g, 'story', s.player === me?.name ? 'My story' : s.player,
                               s.text, s.player === me?.name)}
            {/each}
            {#if iFlewIn(g) && !myStory(g)}
              {@render account(g, 'story', 'My story', '', true)}
            {/if}
          {/if}
        </section>
      {/each}
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

  .card { background: #0d1320; border: 1px solid var(--edge); border-radius: 3px;
          padding: 12px 14px; margin-bottom: 8px; }

  .head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 6px;
          font-family: var(--mono); font-size: 13px; color: var(--ink); }
  .nm { flex: 1; min-width: 0; }
  .rnd { font-size: 11px; color: var(--ink-dim); white-space: nowrap; }

  /* One row per side, the scores in their own column so they read down the list. */
  .side { display: flex; align-items: baseline; gap: 8px; font-family: var(--mono);
          font-size: 11px; margin-top: 2px; }
  .fname { min-width: 74px; color: var(--hull); }
  .fscore { min-width: 44px; text-align: right; color: var(--amber);
            font-variant-numeric: tabular-nums; }
  .crew { flex: 1; min-width: 0; color: var(--ink-dim); }

  .prose { font-size: 12.5px; line-height: 1.65; color: var(--ink); max-width: 70ch; }
  .prose :global(p) { margin: 8px 0; }
  .prose :global(h3), .prose :global(h4), .prose :global(h5) {
    margin: 12px 0 4px; font-size: 11px; font-weight: 600; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--hull);
  }
  .prose :global(ul), .prose :global(ol) { margin: 8px 0; padding-left: 20px; }
  .prose :global(li) { margin: 2px 0; }
  .prose :global(strong) { color: var(--hull); }

  .story { border-top: 1px solid var(--edge); margin-top: 10px; }
  /* Editing sits under the thing it edits, at the end of it. */
  .story .act { justify-content: flex-end; }
  .story h2 { margin: 8px 0 0; font-family: var(--mono); font-size: 11px; font-weight: 600;
              letter-spacing: 0.1em; text-transform: uppercase; color: var(--ink-dim); }

  .none { margin: 8px 0 0; font-size: 12.5px; color: var(--ink-faint); }

  textarea {
    margin-top: 8px;
    width: 100%; box-sizing: border-box; resize: vertical;
    font-family: var(--mono); font-size: 12.5px; line-height: 1.6; color: var(--ink);
    background: #080b12; border: 1px solid var(--edge); border-radius: 3px; padding: 7px 10px;
  }
  textarea:focus { border-color: var(--cyan); outline: none; }
  textarea::placeholder { color: var(--ink-faint); }

  .act { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
  button {
    font-family: var(--mono); font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--amber); background: transparent; border: 1px solid var(--edge); border-radius: 3px;
    padding: 6px 12px; cursor: pointer;
  }
  button:hover:not(:disabled) { border-color: var(--amber); }
  button:disabled { opacity: 0.4; cursor: default; }
  button.go { color: var(--cyan); }
  button.go:hover:not(:disabled) { border-color: var(--cyan); }
  /* The one thing most people came for, so it sits where a card is finished reading. */
  .replay { margin-left: auto; }

  .hint { margin: 6px 0 0; font-size: 11.5px; line-height: 1.5; color: var(--ink-faint); }
  .err { margin: 8px 0 0; font-size: 12px; color: var(--warn); }
  .msg { font-size: 13px; color: var(--ink); line-height: 1.6; }
  .msg.err { color: var(--warn); }
  .msg.quiet { color: var(--ink-faint); }

  @media (max-width: 620px) {
    .screen { padding: 16px 12px 28px; }
  }
</style>