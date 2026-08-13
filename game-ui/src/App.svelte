<script>
  import Selector from './lib/Selector.svelte'
  import FactionMap from './lib/FactionMap.svelte'
  import ShipTypes from './lib/ShipTypes.svelte'
  import Lore from './lib/Lore.svelte'
  import Login from './lib/Login.svelte'
  import OpenGames from './lib/OpenGames.svelte'
  import Solo from './lib/Solo.svelte'
  import TopBar from './lib/TopBar.svelte'
  import Valhalla from './lib/Valhalla.svelte'
  import Replay from './lib/replay/Replay.svelte'

  // The whole view lives in the URL: ?game=xke&player=Menno&round=2, or ?page=ships. That way
  // the admin UI can link straight to a player's map, any view can be shared, and back/forward
  // work.
  function readUrl() {
    const q = new URLSearchParams(location.search)
    const round = q.get('round'), tick = q.get('tick')
    return {
      game: q.get('game'), player: q.get('player'),
      round: round === null ? null : Number(round),
      // Where a replay is being watched from, as an abs tick, and whose side it is watched from.
      tick: tick === null ? null : Number(tick),
      faction: q.get('faction'),
      page: q.get('page'),
      // Which map shell to use. Left off, the browser is asked whether it has fingers.
      ui: q.get('ui'),
    }
  }

  let route = $state(readUrl())
  let me = $state(null)
  let checking = $state(true)
  let notice = $state(null)
  // A director is a commander too. This drops them to what one of their players sees, both to
  // plan their own ships without the noise and to check the experience.
  let asPlayer = $state(false)
  const directing = $derived(!!me?.is_director && !asPlayer)

  function go(next) {
    const q = new URLSearchParams()
    if (next.page) q.set('page', next.page)
    if (next.game) q.set('game', next.game)
    if (next.player) q.set('player', next.player)
    if (next.round !== null && next.round !== undefined) q.set('round', String(next.round))
    if (next.tick !== null && next.tick !== undefined) q.set('tick', String(next.tick))
    if (next.faction) q.set('faction', next.faction)
    if (next.ui) q.set('ui', next.ui)
    history.pushState({}, '', q.size ? `?${q}` : location.pathname)
    route = next
  }

  // A playhead moves too often to push: the tick is written into the URL you are already on, so
  // the view is still shareable and the back button still goes back where you came from.
  function goTick(tick) {
    const q = new URLSearchParams(location.search)
    q.set('tick', String(tick))
    history.replaceState({}, '', `?${q}`)
  }

  // `ui` rides along everywhere, so trying the touch shell on a desktop survives navigating.
  const home = () => go({ game: null, player: null, round: null, tick: null, faction: null,
                          page: null, ui: route.ui })
  const openPage = (page) => go({ game: null, player: null, round: null, tick: null, faction: null,
                                  page, ui: route.ui })

  // A game's hours are the server's, so its clock is what a deadline means. Everything the
  // pages show is in the reader's own time; the server's is only ever displayed.
  let server = $state(null)
  let askedAtMs = $state(0)
  let nowMs = $state(Date.now())
  // What this browser's clock is out by, so a wrong one cannot make a countdown lie.
  const skew = $derived(server ? Date.parse(server.now) - askedAtMs : 0)

  function offsetMsOf(iso) {
    const signed = /([+-])(\d{2}):(\d{2})$/.exec(iso)
    return signed
      ? (signed[1] === '-' ? -1 : 1) * (Number(signed[2]) * 60 + Number(signed[3])) * 60000
      : 0
  }

  // The server's zone has no name here, only an offset, so shift the epoch by it and read the
  // UTC fields. Formatting in the browser's zone would show the reader's clock, not the server's.
  const serverClock = $derived(
    server ? new Date(nowMs + skew + offsetMsOf(server.now)).toISOString().slice(11, 16) : '',
  )

  // A ?login=<token> link is traded for the cookie once and then taken out of the URL, so a
  // bookmarked or shared view never carries someone's identity with it.
  async function claimLinkToken() {
    const q = new URLSearchParams(location.search)
    const token = q.get('login')
    if (!token) return null
    const res = await fetch('/api/game/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    })
    q.delete('login')
    history.replaceState({}, '', q.size ? `?${q}` : location.pathname)
    route = readUrl()
    if (res.ok) return await res.json()
    notice = (await res.json()).detail ?? 'That link did not work.'
    return null
  }

  async function establish() {
    me = await claimLinkToken()
    if (!me) {
      const res = await fetch('/api/game/me')
      if (res.ok) me = await res.json()
    }
    checking = false
  }

  async function signOut() {
    await fetch('/api/game/logout', { method: 'POST' })
    me = null
    notice = null
    home()
  }

  $effect(() => {
    establish()
    const onPop = () => (route = readUrl())
    addEventListener('popstate', onPop)
    return () => removeEventListener('popstate', onPop)
  })

  $effect(() => {
    (async () => {
      const asked = Date.now()
      const res = await fetch('/api/game/time')
      if (res.ok) {
        server = await res.json()
        askedAtMs = asked
      }
    })()
    const ticking = setInterval(() => (nowMs = Date.now()), 30000)
    return () => clearInterval(ticking)
  })
</script>

{#if checking}
  <p class="waiting">…</p>
{:else if route.page === 'valhalla' && route.game}
  <!-- A game that is over, and no login: the museum is the one replay anybody may open. -->
  {#key `${route.game}/${route.faction}`}
    <Replay game={route.game} faction={route.faction} tick={route.tick} museum
            onTick={goTick} onFaction={(f) => go({ ...route, faction: f, tick: null })}
            onLeave={() => openPage('valhalla')} />
  {/key}
{:else if me && route.page === 'replay' && route.game}
  <!-- A game and a side rather than a player: whose war is being watched decides what the API
       will even send. Keyed on both, so either one is a fresh playhead. -->
  {#key `${route.game}/${route.faction}`}
    <Replay game={route.game} faction={route.faction} tick={route.tick} {directing}
            onTick={goTick} onFaction={(f) => go({ ...route, faction: f, tick: null })}
            onLeave={home} />
  {/key}
{:else if me && route.game && route.player}
  <FactionMap game={route.game} player={route.player} round={route.round} ui={route.ui}
              onRound={(r) => go({ ...route, round: r })}
              onLeave={home} />
{:else if !me && !route.page}
  <Login onLoggedIn={(who) => { me = who; notice = null }} onPage={openPage} message={notice} />
{:else}
  <!-- The reference pages are open, so someone deciding whether to join can read them first. -->
  <div class="shell">
    <TopBar {me} {directing} {asPlayer} page={route.page} clock={serverClock} zone={server?.zone ?? ''}
            onToggleAsPlayer={() => (asPlayer = !asPlayer)}
            onPage={openPage} onHome={home} onSignOut={signOut} />
    <div class="page">
      {#if route.page === 'ships'}
        <ShipTypes />
      {:else if route.page === 'lore'}
        <Lore />
      {:else if route.page === 'valhalla'}
        <Valhalla onOpen={(game) => go({ game, player: null, round: null, tick: null,
                                         faction: null, page: 'valhalla', ui: route.ui })} />
      {:else if route.page === 'register' && me}
        <!-- Registering is its own page: it matters for a week and would sit on the list forever. -->
        <OpenGames />
      {:else if route.page === 'solo' && me}
        <Solo onOpen={(game) => go({ game, player: me.name, round: null, page: null, ui: route.ui })} />
      {:else}
        <Selector {me} {directing} {skew} {nowMs}
                  onPick={(game, player) => go({ game, player, round: null, page: null, ui: route.ui })}
                  onReplay={(game) => go({ game, player: null, round: null, tick: null,
                                           page: 'replay', ui: route.ui })}
                  onPage={openPage} />
      {/if}
    </div>
  </div>
{/if}

<style>
  .waiting { height: 100%; display: flex; align-items: center; justify-content: center;
             margin: 0; color: var(--ink-faint); }
  .shell { height: 100%; display: flex; flex-direction: column; background: var(--bg); }
  .page { flex: 1; min-height: 0; }
</style>