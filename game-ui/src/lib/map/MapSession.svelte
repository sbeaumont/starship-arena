<script>
  import { Planning } from "./planning.svelte.js";
  import { Camera } from "./camera.svelte.js";
  import { framePoints } from "./plan.js";
  import DesktopMap from "./DesktopMap.svelte";
  import TouchMap from "./TouchMap.svelte";

  // One game, one player, however many rounds you step through. Mounted per game and player and
  // thrown away with them, so the plan and the camera are made once here rather than rebuilt by
  // something that is allowed to run again.
  let { game, player, round = null, touch = false, onRound, onLeave } = $props();

  // The initial value is the only value: FactionMap keys this component on the pair, so another
  // game or player is another instance rather than a change to this one.
  // svelte-ignore state_referenced_locally
  const planning = new Planning(game, player);
  const camera = new Camera();

  const layers = $state({
    grid: true, paths: true, fire: true, scan: true, tracks: true, explosions: true, hits: true,
    enemyOrdnance: true, friendlyOrdnance: true,
  });

  // Stepping to another round is a fresh picture and the same camera: the point of going back is
  // to compare the same patch of space.
  $effect(() => { planning.load(round); });

  const fit = () => camera.fitTo(framePoints(planning.plan, planning.chains));

  // Framed once, when there is finally something to frame. After that, where you are looking is
  // yours.
  let framed = $state(false);
  $effect(() => {
    if (framed || !planning.plan || !camera.boxW || !camera.boxH) return;
    fit();
    framed = true;
  });

  // Polled while you wait. Push would need a connection held open, and the host has two workers.
  const PULSE_MS = 20000;

  $effect(() => {
    const beat = () => planning.pulse();
    const id = setInterval(beat, PULSE_MS);
    document.addEventListener("visibilitychange", beat);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", beat);
    };
  });
</script>

{#if touch}
  <TouchMap {planning} {camera} {layers} {onRound} {onLeave} onFit={fit} />
{:else}
  <DesktopMap {planning} {camera} {layers} {onRound} {onLeave} onFit={fit} />
{/if}
