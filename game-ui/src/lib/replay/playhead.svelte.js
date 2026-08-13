import { N, NAMED } from "../map/plan.js";

// Where a game is being watched from: which tick, how much trail behind it, and whether it is
// running. The whole record is fetched once, so stepping and playing never wait for the server.

// An abs tick is round × 10 + tick, which is the engine's number for ordering across rounds. This
// is the one place the browser turns it back into a round and a tick.
export const roundOf = (abs) => Math.floor((abs - 1) / N);
export const tickOf = (abs) => abs - roundOf(abs) * N;

// One hue per faction, taken in the order the payload lists them, so nothing here names a faction.
// The side being watched takes the amber the map draws your own ships in and the next one takes
// the red it draws theirs, so a two-sided war reads here the way it does on the map. None of them
// is the orange of a blast or the light a beam is drawn in: a faction is not something that
// happened. Order is worth as much as the hues, since a war of three uses only the first three.
const SIDES = ["#ffb454", "#ff4d5e", "#57d8ff", "#57d98a", "#ff5fd0"];
const NOBODY = "#7b86a4";

export class Playhead {
  data = $state(null);
  loading = $state(true);
  error = $state(null);

  at = $state(0);
  tail = $state(3);
  playing = $state(false);
  perSecond = $state(3);

  // `museum` is a game that is over, read out of Valhalla. The same payload either way: which
  // shelf it came off is the server's business, and it is the only thing this knows about it.
  constructor(game, { faction = null, from = null, asPlayer = false, museum = false } = {}) {
    this.game = game;
    this.faction = faction;
    this.from = from;
    this.asPlayer = asPlayer;
    this.museum = museum;
  }

  async load() {
    const asked = new URLSearchParams();
    if (this.faction) asked.set("faction", this.faction);
    // A director watching as one of their commanders is filtered like one, rather than being
    // handed every side and shown a slice of it.
    if (this.asPlayer && !this.museum) asked.set("as_player", "true");
    const where = this.museum ? `/api/game/valhalla/${this.game}/replay`
                              : `/api/game/${this.game}/replay`;
    try {
      const res = await fetch(where + (asked.size ? `?${asked}` : ""));
      if (!res.ok) {
        throw new Error(res.status === 403 ? "A replay is the director's to open."
                                          : `API returned ${res.status}`);
      }
      this.data = await res.json();
      // A replay opens where the game did; a tick out of range in a shared link falls back to it.
      this.at = (this.from >= this.first && this.from <= this.last) ? this.from : this.first;
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
  // exactly what was known.
  //
  // `killed` is the moment something died, and only the things that leave a wreck can. Anything
  // else that runs out of path was spent rather than killed: a rocket that burned out has simply
  // stopped being there, and the map marks that with nothing at all.
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
        killed: !o.contact && NAMED.has(o.category_name)
                && o.path[o.path.length - 1] === now && !this.atEnd,
      });
    }
    return out;
  });

  // What blows covered on this tick, and only this one: both are gone by the next. A beam is the
  // gap it crossed, a blast is the ground it took in.
  beams = $derived((this.data?.beams ?? []).filter((b) => b.abs_tick === this.at));
  explosions = $derived((this.data?.explosions ?? []).filter((b) => b.abs_tick === this.at));

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