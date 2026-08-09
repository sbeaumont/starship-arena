<script>
  import MapSession from "./map/MapSession.svelte";

  let { game, player, round = null, ui = null, onRound, onLeave } = $props();

  // Which shell: fingers rather than width, because a tablet in landscape is wide and still wants
  // them. `?ui=` overrides, so either can be opened on any machine.
  const coarse = matchMedia("(pointer: coarse)");
  let fingers = $state(coarse.matches);
  $effect(() => {
    const on = (e) => (fingers = e.matches);
    coarse.addEventListener("change", on);
    return () => coarse.removeEventListener("change", on);
  });

  const touch = $derived(ui ? ui === "touch" : fingers);
</script>

<!-- Another game or another player is another session: a fresh plan, and a camera that has not
     been pointed anywhere yet. -->
{#key `${game}/${player}`}
  <MapSession {game} {player} {round} {touch} {onRound} {onLeave} />
{/key}
