<script>
  import Selector from './lib/Selector.svelte'
  import FactionMap from './lib/FactionMap.svelte'
  import ShipTypes from './lib/ShipTypes.svelte'
  import Lore from './lib/Lore.svelte'
  import Login from './lib/Login.svelte'

  // The whole view lives in the URL: ?game=xke&player=Menno&round=2, or ?page=ships. That way
  // the admin UI can link straight to a player's map, any view can be shared, and back/forward
  // work.
  function readUrl() {
    const q = new URLSearchParams(location.search)
    const round = q.get('round')
    return {
      game: q.get('game'), player: q.get('player'),
      round: round === null ? null : Number(round),
      page: q.get('page'),
    }
  }

  let route = $state(readUrl())
  let me = $state(null)
  let checking = $state(true)
  let notice = $state(null)

  function go(next) {
    const q = new URLSearchParams()
    if (next.page) q.set('page', next.page)
    if (next.game) q.set('game', next.game)
    if (next.player) q.set('player', next.player)
    if (next.round !== null && next.round !== undefined) q.set('round', String(next.round))
    history.pushState({}, '', q.size ? `?${q}` : location.pathname)
    route = next
  }

  const home = () => go({ game: null, player: null, round: null, page: null })
  const openPage = (page) => go({ game: null, player: null, round: null, page })

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
</script>

<!-- The reference pages are open, so someone deciding whether to join can read them first. -->
{#if route.page === 'ships'}
  <ShipTypes onLeave={home} />
{:else if route.page === 'lore'}
  <Lore onLeave={home} />
{:else if checking}
  <p class="waiting">…</p>
{:else if !me}
  <Login onLoggedIn={(who) => { me = who; notice = null }} onPage={openPage} message={notice} />
{:else if route.game && route.player}
  <FactionMap game={route.game} player={route.player} round={route.round}
              onRound={(r) => go({ ...route, round: r })}
              onLeave={home} />
{:else}
  <Selector {me} onPick={(game, player) => go({ game, player, round: null, page: null })}
            onPage={openPage} onSignOut={signOut} />
{/if}

<style>
  .waiting { height: 100%; display: flex; align-items: center; justify-content: center;
             margin: 0; color: var(--ink-faint); }
</style>