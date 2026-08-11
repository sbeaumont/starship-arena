import { SvelteSet } from "svelte/reactivity";
import {
  N, ORDER_VERB, orderable, parseOrders, orderLines, simulate,
  defaultParams, needsATarget, NAMED,
} from "./plan.js";

// One round of planning for one player: the picture the API sent, the orders being drawn on top
// of it, and what is selected. Both shells drive this; neither keeps a second copy of any of it.

export class Planning {
  plan = $state(null);
  loading = $state(true);
  error = $state(null);

  // Orders per own ship: the movement the player draws, the weapon orders per tick, and anything
  // else already on file (activations, boosts) which travels through untouched.
  orders = $state({});
  // What the game currently holds for each ship, so a course can be reset back to it.
  baseline = $state({});

  selected = $state(null);
  selectedTick = $state(null);   // which node's weapons we are looking at
  aiming = $state(null);         // weapon waiting for a target to be picked

  ready = $state(false);
  settingReady = $state(false);
  sending = $state(false);
  saveMsg = $state("");
  moved = $state(null);          // a newer round exists than the one being looked at
  locked = new SvelteSet();      // per ship, this session only

  #token = 0;

  constructor(game, player) {
    this.game = game;
    this.player = player;
  }

  async load(round) {
    const mine = ++this.#token;
    this.loading = true;
    this.error = null;
    const url = `/api/game/${this.game}/players/${this.player}/plan`
              + (round === null ? "" : `?round=${round}`);
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      const data = await res.json();
      if (mine !== this.#token) return;
      this.#adopt(data);
    } catch (e) {
      if (mine === this.#token) this.error = String(e);
    } finally {
      if (mine === this.#token) this.loading = false;
    }
  }

  #adopt(data) {
    const o = {}, b = {};
    for (const s of data.ships) if (s.owned) { o[s.name] = parseOrders(s.commands, s); b[s.name] = s.commands; }
    this.plan = data;
    this.orders = o;
    this.baseline = b;
    const own = data.ships.filter((s) => s.owned);
    const first = own.find((s) => s.category_name === "Ship") ?? own[0];
    this.selected = first ? first.name : null;
    this.selectedTick = null;
    this.aiming = null;
    this.saveMsg = "";
    this.ready = data.ready;
    this.locked.clear();
    this.moved = null;
  }

  // Only the newest round can still be planned: everything before it already happened.
  editable = $derived(this.plan ? this.plan.round === this.plan.last_round : false);

  ownShips = $derived(this.plan ? this.plan.ships.filter((s) => s.owned) : []);

  // What a faction mate has on file, read the same way but never written back. A mate who has
  // saved nothing has no plan to show, which is the difference from your own ships: those always
  // have one, because an empty plan is what you start from.
  allyOrders = $derived.by(() => {
    const out = {};
    if (this.plan) {
      for (const s of this.plan.ships) {
        if (!s.owned && s.commands.length) out[s.name] = parseOrders(s.commands, s);
      }
    }
    return out;
  });

  ordersOf = (s) => (s.owned ? this.orders[s.name] : this.allyOrders[s.name]);

  chains = $derived.by(() => {
    const out = {};
    if (!this.plan) return out;
    for (const s of this.plan.ships) {
      const o = this.ordersOf(s);
      if (o) out[s.name] = simulate(s, o);
    }
    return out;
  });

  // Every name the map draws, and so everything a tap can reach.
  drawn = $derived(new Set(this.plan
    ? [...this.plan.ships.map((s) => s.name), ...this.plan.contacts.map((c) => c.name)]
    : []));

  ship = $derived(this.ownShips.find((s) => s.name === this.selected) ?? null);
  chain = $derived(this.selected ? this.chains[this.selected] ?? null : null);
  shipOrders = $derived(this.selected ? this.orders[this.selected] ?? null : null);
  orderableComponents = $derived(this.ship ? orderable(this.ship) : []);

  // Anything not yet saved, so the save button can say so rather than always looking urgent.
  dirty = $derived.by(() =>
    this.ownShips.some((s) => {
      const now = this.orders[s.name] ? orderLines(this.orders[s.name]) : [];
      const was = this.baseline[s.name] ?? [];
      return now.length !== was.length || now.some((l, i) => l !== was[i]);
    })
  );

  counts = $derived.by(() => {
    if (!this.plan) return { ships: 0, enemyOrd: 0, friendlyOrd: 0, enemyShips: 0 };
    const cs = this.plan.contacts.filter((c) => !c.radius);
    const ord = cs.filter((c) => !NAMED.has(c.category_name));
    return {
      ships: cs.filter((c) => NAMED.has(c.category_name)).length,
      enemyOrd: ord.filter((c) => c.stance === "Foe").length,
      friendlyOrd: ord.filter((c) => c.stance === "Friend").length,
      enemyShips: cs.filter((c) => NAMED.has(c.category_name) && c.stance === "Foe").length,
    };
  });

  // ===== Selection =====

  selectShip(name) {
    if (name === this.selected) return;
    this.selected = name;
    this.selectedTick = null;
    this.aiming = null;
  }

  // ===== Weapons =====

  // Ammo is a whole-game budget, so what is left is the live count minus everything this plan
  // already spends across all ten ticks.
  plannedShots(weaponName) {
    if (!this.shipOrders) return 0;
    let n = 0;
    for (let t = 1; t <= N; t++) if (this.shipOrders.fire[t]?.[weaponName]) n++;
    return n;
  }

  ammoLeft = (w) => (w.ammo === null ? null : w.ammo - this.plannedShots(w.name));

  // Whether arming this one waits for a tap, which is what its button has to say.
  aims = (w) => needsATarget(w, this.drawn);

  orderAt = (tick, weaponName) =>
    (this.shipOrders && tick ? this.shipOrders.fire[tick]?.[weaponName] : undefined);

  compOrderAt = (tick, name) =>
    (this.shipOrders && tick ? this.shipOrders.comp[tick]?.[name] : undefined);

  arm(weapon) {
    if (!this.selectedTick || !this.shipOrders) return;
    const left = this.ammoLeft(weapon);
    if (left !== null && left <= 0) return;
    // A weapon that names something on the map waits for it to be tapped, and is armed by the
    // tap. One whose names are drawn nowhere picks off its list: a wreck is not on the map.
    if (needsATarget(weapon, this.drawn)) {
      this.aiming = weapon.name;
      return;
    }
    if (!this.shipOrders.fire[this.selectedTick]) this.shipOrders.fire[this.selectedTick] = {};
    this.shipOrders.fire[this.selectedTick][weapon.name] = defaultParams(weapon);
    this.saveMsg = "";
  }

  pickTarget(contactName) {
    if (!this.aiming || !this.selectedTick || !this.shipOrders) return;
    if (!this.shipOrders.fire[this.selectedTick]) this.shipOrders.fire[this.selectedTick] = {};
    this.shipOrders.fire[this.selectedTick][this.aiming] = [contactName];
    this.aiming = null;
    this.saveMsg = "";
  }

  unarm(tick, weaponName) {
    if (!this.shipOrders?.fire[tick]) return;
    delete this.shipOrders.fire[tick][weaponName];
    if (!Object.keys(this.shipOrders.fire[tick]).length) delete this.shipOrders.fire[tick];
    this.saveMsg = "";
  }

  setParam(tick, weaponName, index, value) {
    this.shipOrders.fire[tick][weaponName][index] = String(value);
    this.saveMsg = "";
  }

  // ===== Components that take an order without being aimed: shields, ECM =====

  armComponent(c) {
    if (!this.selectedTick || !this.shipOrders) return;
    // Starts at nothing so the order does not spend energy the player never asked for.
    const params = c.inputs.map((i) => (i.choices ? i.choices[0] : String(Math.round(i.min))));
    if (!this.shipOrders.comp[this.selectedTick]) this.shipOrders.comp[this.selectedTick] = {};
    this.shipOrders.comp[this.selectedTick][c.name] = { verb: ORDER_VERB[c.group], params };
    this.saveMsg = "";
  }

  unarmComponent(tick, name) {
    if (!this.shipOrders?.comp[tick]) return;
    delete this.shipOrders.comp[tick][name];
    if (!Object.keys(this.shipOrders.comp[tick]).length) delete this.shipOrders.comp[tick];
    this.saveMsg = "";
  }

  setCompParam(tick, name, index, value) {
    this.shipOrders.comp[tick][name].params[index] = String(value);
    this.saveMsg = "";
  }

  // ===== Course =====

  resetCourse(name) {
    if (!this.baseline[name]) return;
    this.orders[name] = parseOrders(this.baseline[name], this.ownShips.find((s) => s.name === name));
    this.saveMsg = "";
  }

  toggleLock(name) {
    if (this.locked.has(name)) this.locked.delete(name);
    else this.locked.add(name);
  }

  // ===== The server =====

  async saveAll() {
    this.sending = true;
    this.saveMsg = "Saving…";
    const results = [];
    let rejected = false;
    for (const s of this.ownShips) {
      const lines = orderLines(this.orders[s.name]);
      try {
        const res = await fetch(`/api/game/${this.game}/ships/${s.name}/commands`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ lines }),
        });
        const body = await res.json();
        if (body.ok) {
          this.baseline[s.name] = lines;
          results.push(`${s.name}: ${lines.length} order${lines.length === 1 ? "" : "s"}`);
        } else {
          rejected = true;
          results.push(`${s.name}: REJECTED (${body.checks.filter((c) => !c.ok).map((c) => c.line).join(", ")})`);
        }
      } catch (e) {
        rejected = true;
        results.push(`${s.name}: error ${e}`);
      }
    }
    this.saveMsg = results.join(" · ");
    this.sending = false;
    return !rejected;
  }

  // Returns the round to move to when saying ready set everyone off, and null otherwise.
  async toggleReady() {
    const goingReady = !this.ready;
    this.settingReady = true;
    try {
      // Ready can process the round on the spot, so the orders go up first and have to hold.
      if (goingReady && !(await this.saveAll())) {
        this.saveMsg += " · Still not ready.";
        return null;
      }
      const res = await fetch(`/api/game/${this.game}/players/${this.player}/ready`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ready: goingReady }),
      });
      if (!res.ok) return null;
      const body = await res.json();
      this.ready = body.ready;
      if (!body.processed) return null;
      this.saveMsg = "Everyone was ready. The round has been processed.";
      return this.plan.last_round + 1;
    } finally {
      this.settingReady = false;
    }
  }

  // Polled while you wait. Push would need a connection held open, and the host has two workers.
  async pulse() {
    if (document.visibilityState !== "visible" || !this.plan) return;
    const res = await fetch(`/api/game/${this.game}/pulse`);
    if (!res.ok) return;
    const p = await res.json();
    for (const s of this.plan.ships) if (s.player in p.ready) s.player_ready = p.ready[s.player];
    if (p.last_round > this.plan.last_round) this.moved = p.last_round;
  }
}
