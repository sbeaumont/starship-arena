import { N } from "../map/plan.js";

// Where a game is being watched from: which tick, how much trail behind it, and whether it is
// running. The whole record is fetched once, so stepping and playing never wait for the server.

// An abs tick is round × 10 + tick, which is the engine's number for ordering across rounds. This
// is the one place the browser turns it back into a round and a tick.
export const roundOf = (abs) => Math.floor((abs - 1) / N);
export const tickOf = (abs) => abs - roundOf(abs) * N;

// One hue per faction, taken in the order the payload lists them, so nothing here names a faction.
const SIDES = ["#ffb454", "#57d8ff", "#57d98a", "#c98cff", "#ff8f5d"];
const NOBODY = "#7b86a4";

export class Playhead {
  data = $state(null);
  loading = $state(true);
  error = $state(null);

  at = $state(0);
  tail = $state(3);
  playing = $state(false);
  perSecond = $state(3);

  constructor(game, { faction = null, from = null, asPlayer = false } = {}) {
    this.game = game;
    this.faction = faction;
    this.from = from;
    this.asPlayer = asPlayer;
  }

  async load() {
    const asked = new URLSearchParams();
    if (this.faction) asked.set("faction", this.faction);
    // A director watching as one of their commanders is filtered like one, rather than being
    // handed every side and shown a slice of it.
    if (this.asPlayer) asked.set("as_player", "true");
    try {
      const res = await fetch(`/api/game/${this.game}/replay`
                              + (asked.size ? `?${asked}` : ""));
      if (!res.ok) {
        throw new Error(res.status === 403 ? "A replay is the director's to open."
                                          : `API returned ${res.status}`);
      }
      this.data = await res.json();
      // A tick out of range in a shared link opens at the end rather than nowhere.
      this.at = (this.from >= this.first && this.from <= this.last) ? this.from : this.last;
    } catch (e) {
      this.error = String(e);
    } finally {
      this.loading = false;
    }
  }

  first = $derived(this.data ? this.data.first_tick : 0);
  last = $derived(this.data ? this.data.last_tick : 0);
  round = $derived(roundOf(this.at));
  tick = $derived(tickOf(this.at));
  atEnd = $derived(this.at >= this.last);

  // The sides in the replay, the one being watched first, so your own ships are the amber the map
  // draws them in and everyone else takes the next hue along.
  sides = $derived.by(() => {
    if (!this.data) return [];
    const all = [...new Set(this.data.objects.map((o) => o.faction).filter(Boolean))].sort();
    const watched = this.data.faction;
    return watched ? [watched, ...all.filter((f) => f !== watched)] : all;
  });

  hue = $derived(Object.fromEntries(this.sides.map((f, i) => [f, SIDES[i % SIDES.length]])));

  // Terrain is on nobody's side, and neither is anything else the game has yet to give one.
  colourOf = (o) => (o.faction ? this.hue[o.faction] : NOBODY);

  // Everything known at the playhead, with the trail behind it. Nothing is drawn for a tick it has
  // no row for: a sighting every third tick reads as a dot, then a trail, then nothing, which is
  // exactly what was known. `gone` is where something of your own died.
  shown = $derived.by(() => {
    if (!this.data) return [];
    const out = [];
    for (const o of this.data.objects) {
      const now = o.path.find((r) => r.abs_tick === this.at);
      if (!now) continue;
      out.push({
        ...o,
        now,
        // By tick rather than by row, so a trail is always the same span of time. Sightings are
        // sparse, and the row before this one can be from ten ticks ago.
        trail: o.path.filter((r) => r.abs_tick > this.at - this.tail && r.abs_tick <= this.at),
        gone: !o.contact && o.path[o.path.length - 1] === now && !this.atEnd,
      });
    }
    return out;
  });

  // What the tick being watched did, whoever it happened to.
  log = $derived.by(() =>
    (this.data?.objects ?? []).flatMap((o) =>
      o.events.filter((e) => e.abs_tick === this.at).map((e) => ({ who: o.name, ...e }))));

  // ===== The transport =====

  goTo(abs) {
    this.at = Math.min(Math.max(abs, this.first), this.last);
  }

  step(by) {
    this.playing = false;
    this.goTo(this.at + by);
  }

  // On the first tick of a round, back means the round before: otherwise the button does nothing.
  toRoundStart() {
    this.step(this.tick === 1 ? -N : -(this.tick - 1));
  }

  toRoundEnd() {
    this.step(this.tick === N ? N : N - this.tick);
  }

  toStart() {
    this.step(this.first - this.at);
  }

  toEnd() {
    this.step(this.last - this.at);
  }

  play() {
    if (this.atEnd) this.at = this.first;   // watching it again, rather than nothing happening
    this.playing = true;
  }

  toggle() {
    if (this.playing) this.playing = false;
    else this.play();
  }

  // One frame of playing. Stops itself at the end so the last tick stays on screen.
  advance() {
    if (this.atEnd) this.playing = false;
    else this.at += 1;
  }
}