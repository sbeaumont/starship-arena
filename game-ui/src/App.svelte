<script>
  import Selector from './lib/Selector.svelte'
  import FactionMap from './lib/FactionMap.svelte'

  // The whole view lives in the URL: ?game=xke&player=Menno&round=2. That way the admin UI
  // can link straight to a player's map, any view can be shared, and back/forward work.
  function readUrl() {
    const q = new URLSearchParams(location.search)
    const round = q.get('round')
    return { game: q.get('game'), player: q.get('player'), round: round === null ? null : Number(round) }
  }

  let route = $state(readUrl())

  function go(next) {
    const q = new URLSearchParams()
    if (next.game) q.set('game', next.game)
    if (next.player) q.set('player', next.player)
    if (next.round !== null && next.round !== undefined) q.set('round', String(next.round))
    history.pushState({}, '', q.size ? `?${q}` : location.pathname)
    route = next
  }

  $effect(() => {
    const onPop = () => (route = readUrl())
    addEventListener('popstate', onPop)
    return () => removeEventListener('popstate', onPop)
  })
</script>

{#if route.game && route.player}
  <FactionMap game={route.game} player={route.player} round={route.round}
              onRound={(r) => go({ ...route, round: r })}
              onLeave={() => go({ game: null, player: null, round: null })} />
{:else}
  <Selector onPick={(game, player) => go({ game, player, round: null })} />
{/if}