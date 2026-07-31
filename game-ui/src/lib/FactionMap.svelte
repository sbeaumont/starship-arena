<script>
  import { SvelteSet } from "svelte/reactivity";

  let { game, player, round = null, onRound, onLeave } = $props();

  const N = 10; // ticks in a round

  // Presentation rule: these categories are named on the map, everything else
  // (missiles, mines, ...) is drawn as a small glyph. Categories come from the API.
  const NAMED = new Set(["Ship", "Starbase"]);

  let plan = $state(null);
  let loading = $state(true);
  let error = $state(null);

  // Layers
  let showEnemyOrdnance = $state(true);
  let showFriendlyOrdnance = $state(true);
  let showTracks = $state(true);
  let showExplosions = $state(true);
  let showPaths = $state(true);
  let showFire = $state(true);
  let showGrid = $state(true);
  let cursor = $state(null);   // world position under the pointer, for orientation

  // Collapsed by default: the map is what you want in front of you when planning.
  let showLog = $state(false);
  let logAllShips = $state(false);
  let everyMessage = $state(false);

  // Orders per own ship: the movement the player draws, the weapon orders per tick, and
  // anything else already on file (activations, boosts) which travels through untouched.
  let orders = $state({});
  // What the game currently holds for each ship, so a course can be reset back to it.
  let baseline = $state({});
  let selected = $state(null);
  let selectedTick = $state(null);   // which node's weapons we are looking at
  let aimingWeapon = $state(null);   // weapon waiting for a target to be clicked
  let saveMsg = $state("");
  let locked = $state(new SvelteSet());   // per ship, this session only
  let ready = $state(false);
  let settingReady = $state(false);
  let moved = $state(null);   // a newer round exists than the one being looked at
  let sending = $state(false);

  // Text sizes live here rather than in the CSS because the de-overlap maths needs them.
  const LABEL_PX = 12.5;
  const GLYPH_PX = 11;
  const CHAR_W = LABEL_PX * 0.6;
  const LINE_H = LABEL_PX + 3;

  const BLAST = { Explosion: "#ff9d4a", Nanocyte: "#7ef0a0", EMP: "#8fb4ff" };
  // Screen px, for the controls rather than for distances: the radius the firing arc is drawn
  // at, and the handle length for the shot being planned.
  const FIRE_LEN = 36;
  const EDIT_LEN = 54;

  // ===== Camera. World-fixed and north-up: view = world with y flipped. `upp` is view
  //       units per screen pixel, so markers sized `px * upp` never change visual size. =====
  let boxW = $state(0);
  let boxH = $state(0);
  let cam = $state({ cx: 0, cy: 0, upp: 2 });
  let fitted = $state(false);
  let svgEl;

  const w2v = (x, y) => ({ vx: x, vy: -y });
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const rad = (d) => (d * Math.PI) / 180;
  const normDelta = (d) => ((d + 180) % 360 + 360) % 360 - 180;

  const vb = $derived.by(() => {
    const w = Math.max(1, boxW) * cam.upp;
    const h = Math.max(1, boxH) * cam.upp;
    return { x: cam.cx - w / 2, y: cam.cy - h / 2, w, h };
  });

  const sx = (vx) => (vx - vb.x) / cam.upp;
  const sy = (vy) => (vy - vb.y) / cam.upp;

  // ===== Orders <-> command lines =====
  const MOVE_RE = /^\s*(\d+)\s*:\s*([RLA])\s*(-?\d+)\s*$/i;
  const FIRE_RE = /^\s*(\d+)\s*:\s*(?:F|FIRE|SCAN)\s+(\S+)\s*(.*)$/i;

  function parseOrders(lines) {
    const turn = Array(N + 1).fill(0), accel = Array(N + 1).fill(0);
    const fire = {}, other = [];
    for (const line of lines) {
      const text = line.trim();
      if (!text) continue;
      const mv = text.match(MOVE_RE);
      if (mv && Number(mv[1]) >= 1 && Number(mv[1]) <= N) {
        const t = Number(mv[1]), op = mv[2].toUpperCase(), v = Number(mv[3]);
        if (op === "A") accel[t] = v; else turn[t] = op === "R" ? v : -v;
        continue;
      }
      const fr = text.match(FIRE_RE);
      if (fr && Number(fr[1]) >= 1 && Number(fr[1]) <= N) {
        const t = Number(fr[1]);
        if (!fire[t]) fire[t] = {};
        fire[t][fr[2]] = fr[3].split(/\s+/).filter(Boolean);
        continue;
      }
      other.push(text);
    }
    return { turn, accel, fire, other };
  }

  function orderLines(o) {
    const rows = [];
    for (let t = 1; t <= N; t++) {
      if (o.turn[t]) rows.push([t, `${t}: ${o.turn[t] > 0 ? "R" : "L"}${Math.abs(o.turn[t])}`]);
      if (o.accel[t]) rows.push([t, `${t}: A${o.accel[t]}`]);
      for (const [wpn, params] of Object.entries(o.fire[t] ?? {})) {
        rows.push([t, `${t}: Fire ${wpn} ${params.join(" ")}`.trim()]);
      }
    }
    for (const line of o.other) {
      const m = line.match(/^\s*(\d+)\s*:/);
      rows.push([m ? Number(m[1]) : N + 1, line]);
    }
    return rows.sort((a, b) => a[0] - b[0]).map((r) => r[1]);
  }

  // ===== Load the faction's picture. Re-runs when the game, player or round changes. =====
  $effect(() => {
    const url = `/api/game/${game}/players/${player}/plan`
              + (round === null ? "" : `?round=${round}`);
    let cancelled = false;
    loading = true;
    error = null;
    (async () => {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        plan = data;
        const o = {}, b = {};
        for (const s of data.ships) if (s.owned) { o[s.name] = parseOrders(s.commands); b[s.name] = s.commands; }
        orders = o;
        baseline = b;
        const own = data.ships.filter((s) => s.owned);
        const first = own.find((s) => s.category_name === "Ship") ?? own[0];
        selected = first ? first.name : null;
        selectedTick = null;
        aimingWeapon = null;
        saveMsg = "";
        ready = data.ready;
        locked.clear();
        moved = null;
      } catch (e) {
        if (!cancelled) error = String(e);
      } finally {
        if (!cancelled) loading = false;
      }
    })();
    return () => { cancelled = true; };
  });

  // A different game or player deserves a fresh camera; stepping through rounds keeps it so
  // the same patch of space can be compared.
  $effect(() => {
    const _who = `${game}/${player}`;
    fitted = false;
  });

  // Only the newest round can still be planned: everything before it already happened.
  const editable = $derived(plan ? plan.round === plan.last_round : false);

  // Everything you command can be given orders. A starbase cannot be given a course - it
  // does not move - but it carries weapons and is one of the heavier platforms in the game.
  const ownShips = $derived(plan ? plan.ships.filter((s) => s.owned) : []);
  const canMove = (s) => s.category_name === "Ship" && s.alive;

  const WRECK_RADIUS = 20;   // world units, like a blast

  // A ray burst, drawn where something died.
  function burst(x, y, r) {
    let d = "";
    for (let i = 0; i < 12; i++) {
      const a = (i * Math.PI) / 6;
      const inner = i % 2 ? r * 0.28 : r * 0.42;
      d += `M${x + Math.sin(a) * inner} ${y - Math.cos(a) * inner}`
         + `L${x + Math.sin(a) * r} ${y - Math.cos(a) * r}`;
    }
    return d;
  }

  // A full value only means something for a quantity: "3 Splinter" against a full "5 Splinter"
  // reads as "3/5 Splinter", while a state like a cloak's just reads as itself.
  function pairText(value, full) {
    if (value === full) return value;
    if (/^\d+$/.test(value) && /^\d+$/.test(full)) return `${value}/${full}`;
    const a = value.match(/^(\d+)\s+(.+)$/);
    const b = full.match(/^(\d+)\s+(.+)$/);
    return a && b && a[2] === b[2] ? `${a[1]}/${b[1]} ${a[2]}` : value;
  }

  // Scoped to the selected ship; the whole faction is several hundred lines a round.
  // One row per tick: what the ship was down to, and what was done to it. Movement and energy
  // are left out; the map shows where it went, and the numbers show the rest.
  const logByTick = $derived.by(() => {
    if (!plan) return [];
    const ships = logAllShips ? plan.ships : plan.ships.filter((s) => s.name === selected);
    const rows = new Map();
    const row = (t) => {
      if (!rows.has(t)) rows.set(t, { tick: t, condition: null, events: [] });
      return rows.get(t);
    };
    for (const s of ships) {
      for (const e of s.events) {
        if (everyMessage || e.kind !== "internal") row(e.tick).events.push({ ship: s.name, ...e });
      }
      if (!logAllShips) for (const c of s.conditions) row(c.tick).condition = c;
    }
    return [...rows.values()].sort((a, b) => a.tick - b.tick);
  });

  function fit() {
    if (!plan || !boxW || !boxH) return;
    const pts = [];
    for (const s of plan.ships) pts.push(w2v(s.x, s.y));
    for (const s of plan.ships) for (const t of s.track) pts.push(w2v(t.x, t.y));
    for (const c of plan.contacts) for (const t of c.track) pts.push(w2v(t.x, t.y));
    // Where your ships are going matters as much as where they are, so the planned courses
    // are framed too rather than leaving you to zoom out and find them.
    for (const chain of Object.values(chains)) for (const n of chain) pts.push(w2v(n.x, n.y));
    if (!pts.length) return;
    const xs = pts.map((p) => p.vx), ys = pts.map((p) => p.vy);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    cam = {
      cx: (minX + maxX) / 2, cy: (minY + maxY) / 2,
      upp: Math.max(Math.max(maxX - minX, 50) / boxW, Math.max(maxY - minY, 50) / boxH) * 1.15,
    };
  }

  $effect(() => { if (!fitted && plan && boxW && boxH) { fit(); fitted = true; } });

  // ===== Something to navigate by. Everything happens around the origin, so the map draws
  //       a grid whose spacing steps through 1/2/5 x 10^n, keeping lines roughly 110px apart
  //       at any zoom, with the axes through 0,0 picked out. =====
  function niceStep(raw) {
    const pow = 10 ** Math.floor(Math.log10(raw));
    const norm = raw / pow;
    return (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10) * pow;
  }

  const grid = $derived.by(() => {
    if (!boxW || !boxH) return { step: 100, xs: [], ys: [] };
    const step = niceStep(cam.upp * 110);
    const xs = [], ys = [];
    for (let x = Math.ceil(vb.x / step) * step; x <= vb.x + vb.w; x += step) xs.push(x);
    for (let y = Math.ceil(vb.y / step) * step; y <= vb.y + vb.h; y += step) ys.push(y);
    return { step, xs, ys };
  });

  // Grid figures are world coordinates; view y runs the other way, hence the minus.
  const gridLabels = $derived.by(() => {
    if (!showGrid) return [];
    const out = [];
    for (const x of grid.xs) out.push({ key: `x${x}`, x: sx(x), y: 13, text: `${Math.round(x)}`, mid: true });
    for (const y of grid.ys) out.push({ key: `y${y}`, x: 7, y: sy(y) - 5, text: `${Math.round(-y)}`, mid: false });
    return out;
  });

  const scaleBarPx = $derived(grid.step / cam.upp);

  // ===== Visible contacts, after decluttering =====
  const contacts = $derived.by(() => {
    if (!plan) return [];
    return plan.contacts.filter((c) => {
      if (NAMED.has(c.category_name)) return true;
      return c.friendly ? showFriendlyOrdnance : showEnemyOrdnance;
    });
  });

  const counts = $derived.by(() => {
    if (!plan) return { ships: 0, enemyOrd: 0, friendlyOrd: 0, enemyShips: 0 };
    const cs = plan.contacts;
    const ord = cs.filter((c) => !NAMED.has(c.category_name));
    return {
      ships: cs.filter((c) => NAMED.has(c.category_name)).length,
      enemyOrd: ord.filter((c) => !c.friendly).length,
      friendlyOrd: ord.filter((c) => c.friendly).length,
      enemyShips: cs.filter((c) => NAMED.has(c.category_name) && !c.friendly).length,
    };
  });

  // ===== Planned courses: the same forward simulation the engine runs =====
  function simulate(s, o) {
    const nodes = [{ t: 0, x: s.x, y: s.y, heading: s.heading, speed: s.speed, atLimit: false }];
    let h = s.heading, sp = s.speed, x = s.x, y = s.y;
    for (let t = 1; t <= N; t++) {
      h += o.turn[t];
      sp = clamp(sp + o.accel[t], -s.limits.max_speed, s.limits.max_speed);
      x += Math.sin(rad(h)) * sp;
      y += Math.cos(rad(h)) * sp;
      nodes.push({ t, x, y, heading: h, speed: sp,
                   atLimit: Math.abs(o.turn[t]) >= s.limits.max_turn ||
                            Math.abs(o.accel[t]) >= s.limits.max_delta_v ||
                            Math.abs(sp) >= s.limits.max_speed });
    }
    return nodes;
  }

  const chains = $derived.by(() => {
    const out = {};
    if (!plan) return out;
    for (const s of ownShips) { const o = orders[s.name]; if (o) out[s.name] = simulate(s, o); }
    return out;
  });

  const selectedShip = $derived(ownShips.find((s) => s.name === selected) ?? null);
  const selectedChain = $derived(selected ? chains[selected] ?? null : null);
  const selectedOrders = $derived(selected ? orders[selected] ?? null : null);

  const viewPath = (nodes) =>
    nodes.map((n) => { const v = w2v(n.x, n.y); return `${v.vx},${v.vy}`; }).join(" ");

  // ===== Weapons =====
  // Ammo is a whole-game budget, so what is left is the live count minus everything this
  // plan already spends across all ten ticks.
  function plannedShots(weaponName) {
    if (!selectedOrders) return 0;
    let n = 0;
    for (let t = 1; t <= N; t++) if (selectedOrders.fire[t]?.[weaponName]) n++;
    return n;
  }
  const ammoLeft = (w) => (w.ammo === null ? null : w.ammo - plannedShots(w.name));

  const orderAt = (tick, weaponName) =>
    (selectedOrders && tick ? selectedOrders.fire[tick]?.[weaponName] : undefined);

  // A weapon's arc is relative to where the ship is pointing at that tick, so a shot's
  // absolute bearing follows the course you drew.
  const nodeAt = (tick) => (selectedChain ? selectedChain[tick] : null);

  const directionIndex = (weapon) => weapon.inputs.findIndex((i) => i.kind === "direction");

  function defaultDirection(weapon) {
    const [lo, hi] = arcRange(weapon);
    return Math.round((lo + hi) / 2);
  }

  // The arc as a straight low..high range of relative angles, for a slider. An arc that
  // wraps through dead ahead (270..90) becomes -90..90.
  function arcRange(weapon) {
    if (!weapon.firing_arc) return [-180, 180];
    const [lo, hi] = weapon.firing_arc;
    return lo > hi ? [lo - 360, hi] : [lo, hi];
  }

  // Angles arrive as -180..180, while an arc that does not pass through dead ahead runs 90..270.
  // Move the angle to the turn of the circle nearest the arc, then hold it between the edges.
  function clampToArc(weapon, angle) {
    const [lo, hi] = arcRange(weapon);
    const mid = (lo + hi) / 2;
    const a = angle - 360 * Math.round((angle - mid) / 360);
    return Math.round(Math.min(hi, Math.max(lo, a)));
  }

  function arm(weapon) {
    if (!selectedTick || !selectedOrders) return;
    const left = ammoLeft(weapon);
    if (left !== null && left <= 0) return;
    // A weapon that names something on the map waits for it to be clicked. One that offers a
    // list picks from that instead: a wreck is not on the map to click.
    if (weapon.inputs.some((i) => i.kind === "object_name" && !i.choices)) {
      aimingWeapon = weapon.name;
      return;
    }
    const params = weapon.inputs.map((i) =>
      i.choices ? (i.choices[0] ?? "")
      : i.kind === "direction" ? String(defaultDirection(weapon))
      : String(Math.round(i.max ?? 0))
    );
    if (!selectedOrders.fire[selectedTick]) selectedOrders.fire[selectedTick] = {};
    selectedOrders.fire[selectedTick][weapon.name] = params;
    saveMsg = "";
  }

  function pickTarget(contactName) {
    if (!aimingWeapon || !selectedTick || !selectedOrders) return;
    if (!selectedOrders.fire[selectedTick]) selectedOrders.fire[selectedTick] = {};
    selectedOrders.fire[selectedTick][aimingWeapon] = [contactName];
    aimingWeapon = null;
    saveMsg = "";
  }

  function unarm(tick, weaponName) {
    if (!selectedOrders?.fire[tick]) return;
    delete selectedOrders.fire[tick][weaponName];
    if (!Object.keys(selectedOrders.fire[tick]).length) delete selectedOrders.fire[tick];
    saveMsg = "";
  }

  // Every planned shot of every ship you command, so a course and its firing read together
  // whether or not that ship is the one being planned.
  const shots = $derived.by(() => {
    if (!plan) return [];
    const out = [];
    for (const ship of ownShips) {
      const o = orders[ship.name], chain = chains[ship.name];
      if (!o || !chain) continue;
      const byName = Object.fromEntries(ship.weapons.map((w) => [w.name, w]));
      const mine = ship.name === selected;
      for (let t = 1; t <= N; t++) {
        for (const [name, params] of Object.entries(o.fire[t] ?? {})) {
          const weapon = byName[name];
          const node = chain[t];
          if (!weapon || !node) continue;
          const listed = Boolean(weapon.inputs[0]?.choices);
          const kind = listed ? "direction" : weapon.inputs[0]?.kind;
          // Whatever it puts in space is named in the order, so say that rather than "SS".
          const label = listed ? params[0] : name;
          const nv = w2v(node.x, node.y);
          const cur = mine && t === selectedTick;
          const key = `${ship.name}:${t}:${name}`;
          if (kind === "object_name") {
            const c = plan.contacts.find((x) => x.name === params[0]);
            out.push({ key, ship: ship.name, mine, tick: t, weapon: name, label, kind, node, nv, cur,
                       target: c ? c.track[c.track.length - 1] : null, targetName: params[0] });
          } else {
            const angle = Number(params[directionIndex(weapon)]) || 0;
            const heading = node.heading + angle;
            // Everything that stands for a real distance is drawn in world units, so it can be
            // read against the grid. Only the handle you drag is sized on screen, because that
            // is a control rather than a distance - except a scanner's, whose distance is
            // itself the cone width and so has to sit where the width puts it.
            const coneIn = coneInput(weapon);
            let end;
            if (coneIn) {
              end = alongWorld(nv.vx, nv.vy, heading,
                               coneRadius(coneIn, Number(params[1]) || coneIn.max));
            } else if (cur) {
              end = along(nv.vx, nv.vy, heading, EDIT_LEN);
            } else if (weapon.payload_speed) {
              // How far the ordnance really travels in a tick.
              end = alongWorld(nv.vx, nv.vy, heading, weapon.payload_speed);
            } else if (weapon.payload) {
              // A mine is launched at the ship's own speed and then slows to a stop, so its
              // first tick covers about that. Dropped at a standstill it stays put, and the
              // arrowhead alone marks the spot.
              end = alongWorld(nv.vx, nv.vy, heading, node.speed);
            } else {
              end = alongWorld(nv.vx, nv.vy, heading, SCAN_REACH);   // a scanner sweep
            }
            out.push({ key, ship: ship.name, mine, tick: t, weapon: name, label, kind: "direction",
                       node, nv, cur, angle, heading, end });
          }
        }
      }
    }
    return out;
  });

  // A weapon that takes a direction plus an angular width sweeps a cone - the gravscan. Show
  // it as you set it, so the sweep can be aimed rather than guessed.
  // World units, for a scanner's arrow and the cone it sweeps, so both scale with the map and
  // can be read against the grid. Ordnance is drawn the distance it really travels; a scan has
  // no such figure, so this is simply an indicative length.
  const SCAN_REACH = 7;

  // A scanner's handle sets both of its inputs at once: turning it aims the sweep, pulling it
  // out narrows the cone. At rest it sits at SCAN_REACH with the cone wide open; pulled to
  // three times that, the cone is at its tightest. That reads the way the game behaves, since
  // a tighter sweep really does see further.
  const coneInput = (weapon) =>
    weapon.inputs.length > 1 && weapon.inputs[1].kind === "number_in_range" ? weapon.inputs[1] : null;

  function coneRadius(inp, width) {
    const tightness = clamp((inp.max - width) / (inp.max - inp.min), 0, 1);
    return SCAN_REACH * (1 + 2 * tightness);
  }

  function coneWidthAt(inp, distance) {
    const pulled = clamp((distance - SCAN_REACH) / (2 * SCAN_REACH), 0, 1);
    return Math.round((inp.max - pulled * (inp.max - inp.min)) / 5) * 5;
  }
  const cones = $derived.by(() => {
    if (!plan) return [];
    const out = [];
    for (const ship of ownShips) {
      const o = orders[ship.name], chain = chains[ship.name];
      if (!o || !chain) continue;
      const byName = Object.fromEntries(ship.weapons.map((w) => [w.name, w]));
      const mine = ship.name === selected;
      for (let t = 1; t <= N; t++) {
        for (const [name, params] of Object.entries(o.fire[t] ?? {})) {
          const w = byName[name];
          const inp = w ? coneInput(w) : null;
          if (!inp) continue;
          const node = chain[t];
          if (!node) continue;
          const width = Number(params[1]) || inp.max;
          out.push({ key: `${ship.name}:${t}:${name}`, mine,
                     nv: w2v(node.x, node.y), heading: node.heading,
                     dir: Number(params[0]) || 0, width, r: coneRadius(inp, width),
                     cur: mine && t === selectedTick });
        }
      }
    }
    return out;
  });

  // ===== Geometry helpers (all marker sizes in screen px via cam.upp) =====
  const trackPoints = (c) =>
    c.track.map((t) => { const v = w2v(t.x, t.y); return `${v.vx},${v.vy}`; }).join(" ");
  const lastOf = (c) => { const t = c.track[c.track.length - 1]; return w2v(t.x, t.y); };

  function courseOf(c) {
    if (c.track.length < 2) return null;
    const a = c.track[c.track.length - 2], b = c.track[c.track.length - 1];
    const dx = b.x - a.x, dy = b.y - a.y;
    if (dx === 0 && dy === 0) return null;
    return (Math.atan2(dx, dy) * 180) / Math.PI;
  }

  const pts = (arr) => arr.map((q) => q.join(",")).join(" ");
  // Along a heading by a length in screen pixels, or in world units.
  const along = (vx, vy, headingDeg, rPx) =>
    [vx + Math.sin(rad(headingDeg)) * rPx * cam.upp, vy - Math.cos(rad(headingDeg)) * rPx * cam.upp];
  const alongWorld = (vx, vy, headingDeg, len) =>
    [vx + Math.sin(rad(headingDeg)) * len, vy - Math.cos(rad(headingDeg)) * len];

  function tri(vx, vy, headingDeg, rPx) {
    const r = rPx * cam.upp, h = rad(headingDeg);
    const p = (a, k) => [vx + Math.sin(a) * r * k, vy - Math.cos(a) * r * k];
    return pts([p(h, 1), p(h + 2.5, 0.62), p(h - 2.5, 0.62)]);
  }
  function diamond(vx, vy, rPx) {
    const r = rPx * cam.upp;
    return pts([[vx, vy - r], [vx + r, vy], [vx, vy + r], [vx - r, vy]]);
  }
  function square(vx, vy, rPx) {
    const r = rPx * cam.upp * 0.85;
    return pts([[vx - r, vy - r], [vx + r, vy - r], [vx + r, vy + r], [vx - r, vy + r]]);
  }

  const SIZE = { Ship: 11, Starbase: 7.5, Missile: 5.5, Mine: 5 };

  function markerFor(category, vx, vy, course) {
    const r = SIZE[category] ?? 5;
    if (category === "Starbase") return square(vx, vy, r);
    if (category === "Mine") return diamond(vx, vy, r);
    if (course === null) return diamond(vx, vy, r * 0.5);
    return tri(vx, vy, course, r);
  }

  // The angular span a weapon covers, drawn at a node and rotated to the heading there.
  // The radius is in world units; a caller wanting a constant screen size passes px * cam.upp.
  function wedge(vx, vy, headingDeg, arc, r) {
    const [lo, hi] = arc;
    const span = ((hi - lo) % 360 + 360) % 360;
    const a = alongWorld(vx, vy, headingDeg + lo, r);
    const b = alongWorld(vx, vy, headingDeg + lo + span, r);
    return `M ${vx},${vy} L ${a[0]},${a[1]} A ${r},${r} 0 ${span > 180 ? 1 : 0} 1 ${b[0]},${b[1]} Z`;
  }


  // ===== Text overlay =====
  const labels = $derived.by(() => {
    if (!plan) return [];
    const items = [];
    for (const s of plan.ships) {
      const v = w2v(s.x, s.y);
      items.push({ key: `s:${s.name}`, x: sx(v.vx), y: sy(v.vy), text: s.name,
                   cls: s.owned ? (s.name === selected ? "sel" : "own") : "ally" });
    }
    for (const c of contacts) {
      if (!NAMED.has(c.category_name)) continue;
      const v = lastOf(c);
      items.push({ key: `c:${c.name}`, x: sx(v.vx), y: sy(v.vy), text: c.name,
                   cls: c.friendly ? "ally" : "enemy" });
    }
    const OFF = 12;
    const placed = [], out = [];
    for (const it of [...items].sort((a, b) => a.y - b.y)) {
      const w = it.text.length * CHAR_W, lx = it.x + OFF;
      let ly = it.y, guard = 0;
      while (guard++ < 80 &&
             placed.some((p) => Math.abs(p.ly - ly) < LINE_H && lx < p.lx + p.w && p.lx < lx + w)) ly += LINE_H;
      placed.push({ lx, ly, w });
      out.push({ ...it, lx, ly, moved: Math.abs(ly - it.y) > 5 });
    }
    return out;
  });

  const glyphs = $derived.by(() =>
    contacts.filter((c) => !NAMED.has(c.category_name)).map((c) => {
      const v = lastOf(c);
      return { key: c.name, x: sx(v.vx), y: sy(v.vy), letter: c.type_name[0],
               enemy: !c.friendly, title: `${c.name} · ${c.type_name}` };
    })
  );

  // Which tick is which node. A ship that comes to a stop parks every remaining tick on the
  // same spot, and a stack of joints otherwise reads as a single one, so a run of ticks
  // sharing a position is labelled as a range.
  const jointLabels = $derived.by(() => {
    if (!showPaths || !selectedChain || !selectedShip || !canMove(selectedShip)) return [];
    const groups = [];
    for (const n of selectedChain.slice(1)) {
      const v = w2v(n.x, n.y);
      const last = groups[groups.length - 1];
      if (last && last.vx === v.vx && last.vy === v.vy) last.ticks.push(n.t);
      else groups.push({ vx: v.vx, vy: v.vy, ticks: [n.t] });
    }
    return groups.map((g) => ({
      key: `${g.ticks[0]}`,
      x: sx(g.vx) + 9,
      y: sy(g.vy) - 9,
      text: g.ticks.length === 1 ? `${g.ticks[0]}` : `${g.ticks[0]}–${g.ticks.at(-1)}`,
    }));
  });

  // Which handle is which weapon: name every planned shot, at its tip.
  const shotLabels = $derived.by(() => {
    if (!showFire) return [];
    return shots.map((s) => {
      if (s.kind === "object_name") {
        if (!s.target) return null;
        const tv = w2v(s.target.x, s.target.y);
        return { key: s.key, x: sx((s.nv.vx + tv.vx) / 2), y: sy((s.nv.vy + tv.vy) / 2),
                 text: s.label, cur: s.cur, mine: s.mine };
      }
      const tip = along(s.end[0], s.end[1], s.heading, 11);   // just beyond the arrow's point
      return { key: s.key, x: sx(tip[0]), y: sy(tip[1]), text: s.label, cur: s.cur, mine: s.mine };
    }).filter(Boolean);
  });

  // ===== Interaction =====
  let panning = false, lastX = 0, lastY = 0;
  let dragK = null, dragShot = null, movedFar = false;
  // A press on one of your ships or its course; acted on only if it turns out to be a click
  // rather than the start of a pan.
  let pendingShip = null;

  function toWorld(e) {
    const rect = svgEl.getBoundingClientRect();
    return { x: vb.x + (e.clientX - rect.left) * cam.upp,
             y: -(vb.y + (e.clientY - rect.top) * cam.upp) };
  }

  function nodeDown(k, e) {
    if (!editable || locked.has(selected)) return;
    dragK = k; movedFar = false;
    lastX = e.clientX; lastY = e.clientY;
    e.stopPropagation();
    svgEl.setPointerCapture(e.pointerId);
  }

  function shotDown(shot, e) {
    // Only the ship being planned has draggable shots. Another ship's shot would have to
    // switch ships and redraw its handle mid-grab, which just reads as the handle jumping.
    if (!editable || !shot.mine) return;
    dragShot = shot; movedFar = false;
    selectedTick = shot.tick;   // grabbing a shot switches planning to its tick
    e.stopPropagation();
    svgEl.setPointerCapture(e.pointerId);
  }

  function onDown(e) {
    panning = true; movedFar = false;
    lastX = e.clientX; lastY = e.clientY;
    svgEl.setPointerCapture(e.pointerId);
  }

  function onMove(e) {
    const w = toWorld(e);
    cursor = { x: Math.round(w.x), y: Math.round(w.y) };
    if (Math.abs(e.clientX - lastX) > 3 || Math.abs(e.clientY - lastY) > 3) movedFar = true;

    if (dragShot !== null) {
      const ship = ownShips.find((s) => s.name === dragShot.ship);
      const w = toWorld(e), node = dragShot.node;
      const weapon = ship.weapons.find((x) => x.name === dragShot.weapon);
      const bearing = (Math.atan2(w.x - node.x, w.y - node.y) * 180) / Math.PI;
      const relative = normDelta(bearing - node.heading);
      const params = orders[dragShot.ship].fire[dragShot.tick][dragShot.weapon];
      params[directionIndex(weapon)] = String(clampToArc(weapon, relative));
      // A scanner takes its cone width from how far out the handle is pulled.
      const coneIn = coneInput(weapon);
      if (coneIn) {
        params[1] = String(coneWidthAt(coneIn, Math.hypot(w.x - node.x, w.y - node.y)));
      }
      return;
    }

    if (dragK !== null) {
      const s = selectedShip, chain = selectedChain, o = selectedOrders;
      if (!s || !chain || !o) return;
      const prev = chain[dragK - 1], w = toWorld(e);
      const dx = w.x - prev.x, dy = w.y - prev.y;
      const dh = clamp(normDelta((Math.atan2(dx, dy) * 180) / Math.PI - prev.heading),
                       -s.limits.max_turn, s.limits.max_turn);
      const dv = clamp(Math.hypot(dx, dy) - prev.speed, -s.limits.max_delta_v, s.limits.max_delta_v);
      const speed = clamp(prev.speed + dv, -s.limits.max_speed, s.limits.max_speed);
      o.turn[dragK] = Math.round(dh);
      o.accel[dragK] = Math.round(speed - prev.speed);
      lastX = e.clientX; lastY = e.clientY;
      return;
    }

    if (!panning) return;
    cam = { ...cam, cx: cam.cx - (e.clientX - lastX) * cam.upp,
                    cy: cam.cy - (e.clientY - lastY) * cam.upp };
    lastX = e.clientX; lastY = e.clientY;
  }

  function selectShip(name) {
    if (name === selected) return;
    selected = name;
    selectedTick = null;
    aimingWeapon = null;
  }

  function onUp(e) {
    // A node pressed without really moving is a click: show that tick's weapons. Clicking one
    // of your ships or its course switches to planning that ship. A click on empty space stops
    // planning a tick, and cancels any pending aim.
    if (dragK !== null && !movedFar) {
      selectedTick = dragK;
    } else if (pendingShip && !movedFar) {
      selectShip(pendingShip);
    } else if (panning && !movedFar && dragShot === null) {
      selectedTick = null;
      aimingWeapon = null;
    }
    panning = false; dragK = null; dragShot = null; pendingShip = null;
    try { svgEl.releasePointerCapture(e.pointerId); } catch (_) {}
  }

  // The wheel always zooms; panning is dragging.
  const WHEEL_ZOOM = 1.06; // per mouse notch
  const NOTCH_PX = 100;    // what a notch reports in pixel mode; Firefox reports 3 lines

  function onWheel(e) {
    e.preventDefault();
    // Normalised to pixels and capped at one notch, so mouse and trackpad both feel the same.
    const px = clamp(e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY, -NOTCH_PX, NOTCH_PX);
    const rect = svgEl.getBoundingClientRect();
    const cxPx = e.clientX - rect.left, cyPx = e.clientY - rect.top;
    const vxAt = vb.x + cxPx * cam.upp, vyAt = vb.y + cyPx * cam.upp;
    const upp = clamp(cam.upp * Math.exp((px * Math.log(WHEEL_ZOOM)) / NOTCH_PX), 0.05, 400);
    cam = { upp, cx: vxAt - cxPx * upp + (boxW * upp) / 2,
                 cy: vyAt - cyPx * upp + (boxH * upp) / 2 };
  }

  function zoomBy(f) { cam = { ...cam, upp: clamp(cam.upp * f, 0.05, 400) }; }
  function centreOn(s) { const v = w2v(s.x, s.y); cam = { ...cam, cx: v.vx, cy: v.vy }; }

  function resetCourse(name) {
    if (!baseline[name]) return;
    orders[name] = parseOrders(baseline[name]);
    saveMsg = "";
  }

  function toggleLock(name) {
    if (locked.has(name)) locked.delete(name);
    else locked.add(name);
  }

  // Polled while you wait. Push would need a connection held open, and the host has two workers.
  const PULSE_MS = 20000;

  $effect(() => {
    game; player;
    const beat = async () => {
      if (document.visibilityState !== "visible" || !plan) return;
      const res = await fetch(`/api/game/${game}/pulse`);
      if (!res.ok) return;
      const p = await res.json();
      for (const s of plan.ships) if (s.player in p.ready) s.player_ready = p.ready[s.player];
      if (p.last_round > plan.last_round) moved = p.last_round;
    };
    const id = setInterval(beat, PULSE_MS);
    const onVisible = () => beat();
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  });

  async function toggleReady() {
    settingReady = true;
    try {
      const res = await fetch(`/api/game/${game}/players/${player}/ready`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ready: !ready }),
      });
      if (!res.ok) return;
      const body = await res.json();
      ready = body.ready;
      if (body.processed) {
        saveMsg = "Everyone was ready. The round has been processed.";
        onRound(plan.last_round + 1);
      }
    } finally {
      settingReady = false;
    }
  }

  async function saveAll() {
    sending = true;
    saveMsg = "Saving…";
    const results = [];
    for (const s of ownShips) {
      const lines = orderLines(orders[s.name]);
      try {
        const res = await fetch(`/api/game/${game}/ships/${s.name}/commands`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ lines }),
        });
        const body = await res.json();
        if (body.ok) {
          baseline[s.name] = lines;
          results.push(`${s.name}: ${lines.length} order${lines.length === 1 ? "" : "s"}`);
        } else {
          results.push(`${s.name}: REJECTED (${body.checks.filter((c) => !c.ok).map((c) => c.line).join(", ")})`);
        }
      } catch (e) {
        results.push(`${s.name}: error ${e}`);
      }
    }
    saveMsg = results.join(" · ");
    sending = false;
  }
</script>

<div class="console">
  <header>
    <button type="button" class="back" onclick={onLeave} title="Choose another game or player">←</button>
    <h1>Starship Arena</h1>
    <span class="sub">
      {#if plan}
        {plan.player} · faction {plan.factions.join(", ")} ·
        {#if editable}planning round {plan.round + 1}{:else}after round {plan.round}{/if}
      {:else}loading…{/if}
    </span>
    <span class="spacer"></span>
    {#if plan}
      <span class="rounds">
        {#each Array(plan.last_round + 1) as _, r (r)}
          <button type="button" class="rbtn" class:on={r === plan.round}
                  onclick={() => onRound(r)}>{r}</button>
        {/each}
      </span>
    {/if}
    {#if moved}
      <button type="button" class="badge moved" onclick={() => onRound(moved)}>
        Round {moved} has been played. Open it
      </button>
    {/if}
    {#if aimingWeapon}<span class="badge aiming">click a target for {aimingWeapon}</span>{/if}
    {#if plan && !editable}<span class="badge past">read only</span>{/if}
    <span class="badge">{game}</span>
  </header>

  <main>
    <aside class="log" class:open={showLog}>
      <button type="button" class="tab" onclick={() => (showLog = !showLog)}
              title={showLog ? "Hide the log" : "What happened this round"}>Log</button>
      {#if showLog && plan}
        <div class="logbody">
          {#if selectedShip}
            <h2>Condition at Tick 0</h2>
            <div class="gauge">
              <span class="gk">Hull</span>
              <span class="gbar"><i class:low={selectedShip.hull / selectedShip.max_hull < 0.34}
                                    style="width: {(100 * selectedShip.hull) / selectedShip.max_hull}%"></i></span>
              <span class="gv">{selectedShip.hull}/{selectedShip.max_hull}</span>
            </div>
            <div class="gauge">
              <span class="gk">Battery</span>
              <span class="gbar"><i class="power"
                                    style="width: {(100 * selectedShip.battery) / selectedShip.max_battery}%"></i></span>
              <span class="gv">{selectedShip.battery}/{selectedShip.max_battery}</span>
            </div>

            {#each selectedShip.components as c (c.name)}
              <div class="comp">
                <span class="cn">{c.name}</span>
                <span class="cs">
                  {#each Object.entries(c.status) as [k, v] (k)}
                    <span class="pair" class:spent={v !== c.full[k]}>
                      {pairText(v, c.full[k])}<span class="pk">{k}</span>
                    </span>
                  {/each}
                </span>
              </div>
            {/each}
          {/if}

          <h2 class:spaced={selectedShip}>Round {plan.round} · {logAllShips ? "faction" : (selected ?? "no ship")}</h2>
          <label class="all"><input type="checkbox" bind:checked={logAllShips} /> all ships</label>
          <label class="all"><input type="checkbox" bind:checked={everyMessage} /> every message</label>
          {#if !logByTick.length}
            <p class="note">{selected ? "Nothing recorded." : "Pick a ship to read its log."}</p>
          {:else}
            {#each logByTick as r (r.tick)}
              <div class="tickrow">
                <span class="t">{r.tick}</span>
                {#if r.condition}
                  <span class="v">hull {r.condition.hull}</span>
                  <span class="v">bat {r.condition.battery}</span>
                  {#each Object.entries(r.condition.shields) as [q, s] (q)}
                    <span class="v"><span class="q">{q}</span>{s}</span>
                  {/each}
                {/if}
              </div>
              <ul>
                {#each r.events as e, i (i)}
                  <li class={e.kind}>
                    {#if logAllShips}<span class="who">{e.ship}</span>{/if}{e.text}
                  </li>
                {/each}
              </ul>
            {/each}
          {/if}
        </div>
      {/if}
    </aside>

    <div class="plot" bind:clientWidth={boxW} bind:clientHeight={boxH}>
      {#if loading}
        <p class="overlay-msg">Loading {player}'s tactical picture…</p>
      {:else if error}
        <p class="overlay-msg err">Couldn't reach the API: {error}</p>
      {/if}

      <!-- Layer 1: geometry, in world coordinates. Pans and zooms. -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <svg bind:this={svgEl} class="world" class:aiming={aimingWeapon}
           viewBox={`${vb.x} ${vb.y} ${vb.w} ${vb.h}`} preserveAspectRatio="none"
           role="img" aria-label="Faction tactical map. Drag to pan, scroll to zoom."
           onpointerdown={onDown} onpointermove={onMove} onpointerup={onUp}
           onpointercancel={onUp} onwheel={onWheel} onpointerleave={() => (cursor = null)}>
        {#if showGrid}
          {#each grid.xs as x (x)}
            <line class="grid" class:axis={x === 0} x1={x} y1={vb.y} x2={x} y2={vb.y + vb.h}
                  stroke-width={cam.upp} />
          {/each}
          {#each grid.ys as y (y)}
            <line class="grid" class:axis={y === 0} x1={vb.x} y1={y} x2={vb.x + vb.w} y2={y}
                  stroke-width={cam.upp} />
          {/each}
          <circle class="origin" cx="0" cy="0" r={6 * cam.upp} stroke-width={1.2 * cam.upp} />
        {/if}
        {#if plan}
          {#if showExplosions}
            {#each plan.explosions as e (`${e.tick}:${e.x}:${e.y}:${e.radius}`)}
              {@const v = w2v(e.x, e.y)}
              <circle class="blast" cx={v.vx} cy={v.vy} r={e.radius}
                      fill={BLAST[e.damage_type] ?? BLAST.Explosion} stroke-width={cam.upp} />
            {/each}
          {/if}

          {#each plan.ships.filter((s) => !s.alive && s.track.length) as s (s.name)}
            {@const last = s.track[s.track.length - 1]}
            {@const v = w2v(last.x, last.y)}
            <path class="wreck" d={burst(v.vx, v.vy, WRECK_RADIUS)} stroke-width={1.4 * cam.upp} />
            <circle class="wreck-core" cx={v.vx} cy={v.vy} r={WRECK_RADIUS * 0.18} />
          {/each}

          {#each contacts as c (c.name)}
            {#if showTracks && c.track.length > 1}
              <polyline class="track" class:enemy={!c.friendly}
                        points={trackPoints(c)} stroke-width={1.2 * cam.upp} />
              {#each c.track.slice(0, -1) as t (t.tick)}
                {@const v = w2v(t.x, t.y)}
                <circle class="mark" class:enemy={!c.friendly} cx={v.vx} cy={v.vy} r={1.6 * cam.upp} />
              {/each}
            {/if}
            {@const v = lastOf(c)}
            <polygon class="blip" class:enemy={!c.friendly}
                     points={markerFor(c.category_name, v.vx, v.vy, courseOf(c))} />
            {#if aimingWeapon}
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <circle class="target-hit" cx={v.vx} cy={v.vy} r={14 * cam.upp}
                      onpointerdown={(e) => { e.stopPropagation(); pickTarget(c.name); }} />
            {/if}
          {/each}

          <!-- Where the faction's ships actually went during the round. Dashed, to read as
               past rather than plan, and joining the ship where the planned course starts. -->
          {#if showTracks && plan}
            {#each plan.ships.filter((s) => s.track.some((t) => t.x !== s.track[0].x || t.y !== s.track[0].y)) as s (s.name)}
              <polyline class="wake" class:sel={s.name === selected} class:ally={!s.owned}
                        points={s.track.map((t) => { const v = w2v(t.x, t.y); return `${v.vx},${v.vy}`; }).join(" ")}
                        stroke-width={1.4 * cam.upp} />
              {#each s.track.slice(0, -1) as t (t.tick)}
                {@const v = w2v(t.x, t.y)}
                <circle class="wake-dot" class:sel={s.name === selected} class:ally={!s.owned}
                        cx={v.vx} cy={v.vy} r={1.8 * cam.upp} />
              {/each}
            {/each}
          {/if}

          {#if showPaths}
            {#each ownShips.filter(canMove) as s (s.name)}
              {#if chains[s.name]}
                {@const isSel = s.name === selected}
                <polyline class="course" class:sel={isSel}
                          points={viewPath(chains[s.name])} stroke-width={2 * cam.upp} />
                {#if !isSel}
                  <!-- Where each tick lands, so another ship's course can be read at a glance
                       without giving it draggable handles. -->
                  {#each chains[s.name].slice(1) as n (n.t)}
                    {@const v = w2v(n.x, n.y)}
                    <circle class="course-dot" cx={v.vx} cy={v.vy} r={2.4 * cam.upp} />
                  {/each}
                {/if}
              {/if}
            {/each}
          {/if}

          {#each plan.ships as s (s.name)}
            {@const v = w2v(s.x, s.y)}
            <circle class="halo" class:own={s.owned} class:sel={s.name === selected}
                    cx={v.vx} cy={v.vy} r={18 * cam.upp} stroke-width={cam.upp} />
            <polygon class="ship" class:own={s.owned}
                     points={markerFor(s.category_name, v.vx, v.vy, s.heading)} />
            {#if s.owned}
              <!-- Clicking one of your ships is how you switch to planning it. -->
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <circle class="ship-hit" cx={v.vx} cy={v.vy} r={16 * cam.upp}
                      onpointerdown={() => (pendingShip = s.name)} />
            {/if}
          {/each}

          <!-- Scan cones, behind everything else. -->
          {#each cones as c (c.key)}
            {#if c.width >= 360}
              <circle class="cone" class:cur={c.cur} class:other={!c.mine}
                      cx={c.nv.vx} cy={c.nv.vy} r={c.r} stroke-width={cam.upp} />
            {:else}
              <path class="cone" class:cur={c.cur} class:other={!c.mine} stroke-width={cam.upp}
                    d={wedge(c.nv.vx, c.nv.vy, c.heading,
                             [c.dir - c.width / 2, c.dir + c.width / 2], c.r)} />
            {/if}
          {/each}

          <!-- Arcs of the weapons ordered at the tick being planned. Drawn before the shots
               so they sit behind them, and they never take the pointer. -->
          {#if selectedTick && selectedShip && nodeAt(selectedTick)}
            {@const node = nodeAt(selectedTick)}
            {@const nv = w2v(node.x, node.y)}
            {#each selectedShip.weapons.filter((w) => w.firing_arc && orderAt(selectedTick, w.name)) as w (w.name)}
              <path class="arc" d={wedge(nv.vx, nv.vy, node.heading, w.firing_arc,
                                         (FIRE_LEN + 8) * cam.upp)} />
            {/each}
          {/if}

          <!-- Planned shots: a branch off the node they are fired from. Shots at other ticks
               stay quiet - a small arrowhead - so the tick being planned stands out. -->
          {#if showFire}
            {#each shots as sh (sh.key)}
              {#if sh.kind === "object_name"}
                {#if sh.target}
                  {@const tv = w2v(sh.target.x, sh.target.y)}
                  <line class="beam" class:cur={sh.cur} class:other={!sh.mine}
                        x1={sh.nv.vx} y1={sh.nv.vy} x2={tv.vx} y2={tv.vy}
                        stroke-width={(sh.cur ? 1.6 : 1.1) * cam.upp} />
                {/if}
              {:else}
                <line class="shot" class:cur={sh.cur} class:other={!sh.mine}
                      x1={sh.nv.vx} y1={sh.nv.vy} x2={sh.end[0]} y2={sh.end[1]}
                      stroke-width={(sh.cur ? 1.8 : 1.1) * cam.upp} />
                {#if sh.mine}
                  <!-- svelte-ignore a11y_no_static_element_interactions -->
                  <circle class="shot-grab" cx={sh.end[0]} cy={sh.end[1]} r={11 * cam.upp}
                          onpointerdown={(e) => shotDown(sh, e)} />
                {/if}
                {#if sh.cur}
                  <circle class="shot-handle" cx={sh.end[0]} cy={sh.end[1]} r={4.5 * cam.upp}
                          stroke-width={2 * cam.upp} />
                {:else}
                  <polygon class="shot-tip" class:other={!sh.mine}
                           points={tri(sh.end[0], sh.end[1], sh.heading, 4)} />
                {/if}
              {/if}
            {/each}
          {/if}

          <!-- Draggable joints, only for the ship being planned. -->
          <!-- Back to front, so tick 1 ends up on top. At a standstill every node sits on
               the ship, and the one you grab should be the first tick: giving it speed pushes
               all the later nodes outwards at once, instead of having to drag each in turn. -->
          {#if showPaths && selectedChain && selectedShip && canMove(selectedShip)}
            {#each selectedChain.slice(1).reverse() as n (n.t)}
              {@const v = w2v(n.x, n.y)}
              {#if editable}
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <!-- pointer-only drag handle; keyboard planning is a later feature -->
                <circle class="grab" cx={v.vx} cy={v.vy} r={13 * cam.upp}
                        onpointerdown={(e) => nodeDown(n.t, e)} />
              {/if}
              <circle class="joint" class:limit={n.atLimit} class:cur={n.t === selectedTick}
                      cx={v.vx} cy={v.vy} r={5 * cam.upp} stroke-width={2 * cam.upp} />
            {/each}
          {/if}
        {/if}
      </svg>

      <!-- Layer 2: all text, in screen pixels. Immune to zoom by construction. -->
      <svg class="text-layer" viewBox={`0 0 ${Math.max(1, boxW)} ${Math.max(1, boxH)}`}
           preserveAspectRatio="none" aria-hidden="true">
        {#each gridLabels as g (g.key)}
          <text class="grid-label" x={g.x} y={g.y} font-size={GLYPH_PX}
                text-anchor={g.mid ? "middle" : "start"}>{g.text}</text>
        {/each}
        {#if showGrid && boxH}
          <line class="scalebar" x1="14" y1={boxH - 18} x2={14 + scaleBarPx} y2={boxH - 18} />
          <line class="scalebar" x1="14" y1={boxH - 22} x2="14" y2={boxH - 14} />
          <line class="scalebar" x1={14 + scaleBarPx} y1={boxH - 22} x2={14 + scaleBarPx} y2={boxH - 14} />
          <text class="grid-label" x={14 + scaleBarPx / 2} y={boxH - 26}
                font-size={GLYPH_PX} text-anchor="middle">{grid.step}</text>
        {/if}
        {#if cursor}
          <text class="cursor-label" x={Math.max(1, boxW) - 12} y={Math.max(1, boxH) - 14}
                font-size={GLYPH_PX} text-anchor="end">{cursor.x}, {cursor.y}</text>
        {/if}
        {#each glyphs as g (g.key)}
          <text class="glyph" class:enemy={g.enemy} x={g.x} y={g.y - 7}
                font-size={GLYPH_PX} text-anchor="middle">
            {g.letter}<title>{g.title}</title>
          </text>
        {/each}
        {#each labels as l (l.key)}
          {#if l.moved}
            <line class="leader" x1={l.x} y1={l.y} x2={l.lx - 2} y2={l.ly - 4} />
          {/if}
          <text class="label {l.cls}" x={l.lx} y={l.ly} font-size={LABEL_PX}>{l.text}</text>
        {/each}
        {#each jointLabels as j (j.key)}
          <text class="tick-label" x={j.x} y={j.y} font-size={GLYPH_PX}>{j.text}</text>
        {/each}
        {#each shotLabels as s (s.key)}
          <text class="shot-label" class:cur={s.cur} class:other={!s.mine} x={s.x} y={s.y}
                font-size={GLYPH_PX} text-anchor="middle">{s.text}</text>
        {/each}
      </svg>

      <div class="zoom">
        <button type="button" onclick={() => zoomBy(1 / 1.15)} aria-label="Zoom in">+</button>
        <button type="button" onclick={() => zoomBy(1.15)} aria-label="Zoom out">−</button>
        <button type="button" onclick={fit}>Fit</button>
      </div>
    </div>

    <aside class="panel">
      <section>
        <h2>Your ships</h2>
        <ul class="ships">
          {#each ownShips as s (s.name)}
            <li>
              <button type="button" class="pick" class:on={s.name === selected} class:gone={!s.alive}
                      onclick={() => { selected = s.name; selectedTick = null; aimingWeapon = null; centreOn(s); }}>
                <span class="lamp" class:lit={s.player_ready}
                      title={s.player_ready ? "you said ready" : "you have not said ready"}></span>
                <span class="nm">{s.name}</span>
                <span class="ty">{s.ship_type}</span>
                <span class="sp">{s.speed}</span>
              </button>
            </li>
          {/each}
          {#if plan}
            {#each plan.ships.filter((s) => !s.owned) as s (s.name)}
              <li class="ally-row">
                <span class="lamp" class:lit={s.player_ready}
                      title={s.player ? `${s.player} is ${s.player_ready ? "ready" : "not ready"}` : ""}></span>
                <span class="nm">{s.name}</span><span class="ty">{s.player ?? s.ship_type}</span>
              </li>
            {/each}
          {/if}
        </ul>
      </section>

      {#if selectedShip}
        <section>
          <details class="fold">
            <summary>Specs · {selectedShip.ship_type}</summary>
            <div class="specs">
              {#each Object.entries(selectedShip.specs) as [k, v] (k)}
                <span class="sk">{k}</span><span class="sv">{v}</span>
              {/each}
            </div>
          </details>
        </section>
      {/if}

      {#if selectedShip && selectedOrders && selectedChain}
        <section>
          <h2>{selectedShip.name} · course</h2>
          <table>
            <thead><tr><th class="t">Tick</th><th>Turn</th><th>Throttle</th><th>Speed</th><th>Fire</th></tr></thead>
            <tbody>
              {#each selectedChain.slice(1) as n (n.t)}
                {@const fired = Object.keys(selectedOrders.fire[n.t] ?? {})}
                <tr class:idle={!selectedOrders.turn[n.t] && !selectedOrders.accel[n.t] && !fired.length}
                    class:cur={n.t === selectedTick}>
                  <td class="t">
                    <button type="button" class="tick-pick" onclick={() => (selectedTick = n.t)}>{n.t}</button>
                  </td>
                  <td>{#if !selectedOrders.turn[n.t]}·{:else}<span class="turn" class:pinned={Math.abs(selectedOrders.turn[n.t]) >= selectedShip.limits.max_turn}>{selectedOrders.turn[n.t] > 0 ? "R" : "L"}{Math.abs(selectedOrders.turn[n.t])}</span>{/if}</td>
                  <td>{#if !selectedOrders.accel[n.t]}·{:else}<span class="accel" class:pinned={Math.abs(selectedOrders.accel[n.t]) >= selectedShip.limits.max_delta_v}>A{selectedOrders.accel[n.t] > 0 ? "+" : ""}{selectedOrders.accel[n.t]}</span>{/if}</td>
                  <td>{n.speed}</td>
                  <td class="fire-cell">{fired.length ? fired.join(",") : "·"}</td>
                </tr>
              {/each}
            </tbody>
          </table>
          <p class="limits-line">
            limits: {selectedShip.limits.max_turn}° turn · Δv {selectedShip.limits.max_delta_v} ·
            max speed {selectedShip.limits.max_speed}
          </p>

          {#if editable}
            <div class="buttons">
              <button type="button" class="ghost-btn" onclick={() => resetCourse(selected)}>Reset course</button>
              <button type="button" class="save" disabled={sending} onclick={saveAll}>Save all</button>
            </div>
            <div class="buttons">
              <button type="button" class="state" class:on={!locked.has(selected)}
                      onclick={() => toggleLock(selected)}
                      title="Stop the course being dragged by accident">
                {locked.has(selected) ? "Locked" : "Unlocked"}
              </button>
              <button type="button" class="state" class:on={ready} disabled={settingReady}
                      onclick={toggleReady}
                      title="Tell the director you are done with this round">
                {ready ? "Ready" : "Not ready"}
              </button>
            </div>
          {:else}
            <p class="note">Round {plan.round} has already been played. Go to round
              {plan.last_round} to give orders.</p>
          {/if}
          {#if saveMsg}
            <p class="savemsg" class:err={saveMsg.includes("REJECTED") || saveMsg.includes("error")}>{saveMsg}</p>
          {/if}
        </section>

        <section class="grow">
          {#if !selectedTick}
            <h2>Weapons</h2>
            <p class="hint">Click a joint on the course, or a tick number above, to give
              {selectedShip.name} weapon orders for that tick.</p>
          {:else}
            <h2>Tick {selectedTick} · weapons</h2>
            <ul class="weapons">
              {#each selectedShip.weapons as w (w.name)}
                {@const existing = orderAt(selectedTick, w.name)}
                {@const left = ammoLeft(w)}
                <li class:armed={existing}>
                  <div class="wrow">
                    <span class="wname">{w.name}</span>
                    {#if !editable}
                      <span></span>
                    {:else if existing}
                      <button type="button" class="wfire on"
                              onclick={() => unarm(selectedTick, w.name)}>clear</button>
                    {:else}
                      <button type="button" class="wfire"
                              disabled={(left !== null && left <= 0)
                                        || (w.inputs[0].choices?.length === 0)}
                              onclick={() => arm(w)}>
                        {w.inputs[0].choices ? "choose"
                         : w.inputs[0].kind === "object_name" ? "pick target" : "fire"}
                      </button>
                    {/if}
                    <span class="wammo" class:out={left !== null && left <= 0}>
                      {#if w.ammo !== null}{left}/{w.max_ammo} {w.payload}{/if}
                    </span>
                  </div>
                  {#if existing}
                    <div class="worder">
                      {#if w.inputs[0].choices}
                        <label class="slider">
                          {w.inputs[0].name}
                          <select value={existing[0]}
                                  onchange={(e) => (selectedOrders.fire[selectedTick][w.name][0] = e.currentTarget.value)}>
                            {#each w.inputs[0].choices as c (c)}<option value={c}>{c}</option>{/each}
                          </select>
                        </label>
                        {#each w.inputs.slice(1) as inp, i (inp.name)}
                          <label class="slider aim">
                            {inp.name}
                            <input type="range" min={arcRange(w)[0]} max={arcRange(w)[1]} step="5"
                                   value={existing[i + 1]}
                                   oninput={(e) => (selectedOrders.fire[selectedTick][w.name][i + 1] = e.currentTarget.value)} />
                            <b>{existing[i + 1]}°</b>
                          </label>
                        {/each}
                      {:else if w.inputs[0].kind === "object_name"}
                        <span class="at">→ {existing[0]}</span>
                      {:else}
                        <label class="slider aim">
                          aim
                          <input type="range" min={arcRange(w)[0]} max={arcRange(w)[1]} step="5"
                                 value={existing[0]}
                                 oninput={(e) => (selectedOrders.fire[selectedTick][w.name][0] = e.currentTarget.value)} />
                          <b>{existing[0]}°</b>
                        </label>
                        {#each w.inputs.slice(1) as inp, i (inp.name)}
                          <label class="slider">
                            {inp.name}
                            <input type="range" min={inp.min} max={inp.max} step="10"
                                   value={existing[i + 1]}
                                   oninput={(e) => (selectedOrders.fire[selectedTick][w.name][i + 1] = e.currentTarget.value)} />
                            <b>{existing[i + 1]}</b>
                          </label>
                        {/each}
                      {/if}
                    </div>
                  {/if}
                </li>
              {/each}
            </ul>
            <p class="note">One order per weapon per tick. Drag a shot's handle on the map to
              re-aim it; the arc turns with the course you plotted.</p>
          {/if}

          {#if selectedOrders.other.length}
            <h2 class="spaced">Other orders</h2>
            <ul class="others">
              {#each selectedOrders.other as line, i (i)}<li>{line}</li>{/each}
            </ul>
          {/if}
        </section>
      {/if}

      <section>
        <h2>Layers</h2>
        <label><input type="checkbox" bind:checked={showGrid} /> Grid &amp; origin</label>
        <label><input type="checkbox" bind:checked={showPaths} /> Planned courses</label>
        <label><input type="checkbox" bind:checked={showFire} /> Weapon orders</label>
        <label><input type="checkbox" bind:checked={showTracks} /> Tracks</label>
        <label><input type="checkbox" bind:checked={showExplosions} /> Explosions ({plan ? plan.explosions.length : 0})</label>
        <label><input type="checkbox" bind:checked={showEnemyOrdnance} /> Enemy ordnance ({counts.enemyOrd})</label>
        <label><input type="checkbox" bind:checked={showFriendlyOrdnance} /> Friendly ordnance ({counts.friendlyOrd})</label>
      </section>

      <section>
        {#if plan}
          <p class="tally">
            {counts.ships} ships/bases (<span class="enemy-txt">{counts.enemyShips} enemy</span>) ·
            {counts.enemyOrd + counts.friendlyOrd} ordnance
          </p>
        {/if}
        <details class="fold">
          <summary>Legend</summary>
          <ul class="legend">
            <li><span class="sw sel-sw"></span>ship being planned</li>
            <li><span class="sw own"></span>your other ships</li>
            <li><span class="sw course-sw"></span>their planned course</li>
            <li><span class="sw ally"></span>faction ally</li>
            <li><span class="sw enemy"></span>enemy contact</li>
            <li><span class="sw blast-sw"></span>explosion (true radius)</li>
          </ul>
          <p class="hint sub-hint">▲ course known · ◆ mine · ■ starbase · small ◆ seen once, course unknown</p>
        </details>
      </section>
    </aside>
  </main>
</div>

<style>
  .console { display: flex; flex-direction: column; height: 100%; min-height: 520px; }

  header {
    display: flex; align-items: baseline; gap: 14px;
    padding: 14px 20px; border-bottom: 1px solid var(--edge);
    background: linear-gradient(#0d1322, #0a0e17);
  }
  header h1 { margin: 0; font-size: 15px; font-weight: 600; letter-spacing: 0.18em; text-transform: uppercase; color: var(--hull); }
  .sub { font-size: 12px; color: var(--ink-dim); letter-spacing: 0.06em; }
  .spacer { flex: 1; }
  .badge { font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--amber);
           border: 1px solid var(--amber); padding: 3px 8px; border-radius: 2px; opacity: 0.9; }
  .badge.aiming { color: var(--cyan); border-color: var(--cyan); }
  .badge.past { color: var(--ink-dim); border-color: var(--ink-faint); }
  .badge.moved { font-family: var(--mono); color: #79b894; border-color: #79b894;
                 background: #121c17; cursor: pointer; }
  .badge.moved:hover { filter: brightness(1.2); }

  .back {
    font-family: var(--mono); font-size: 14px; color: var(--ink-dim);
    background: transparent; border: 1px solid var(--edge); border-radius: 3px;
    padding: 2px 9px; cursor: pointer; line-height: 1.3;
  }
  .back:hover { color: var(--cyan); border-color: var(--cyan); }
  .back:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }

  .rounds { display: flex; gap: 3px; }
  .rbtn {
    font-family: var(--mono); font-size: 11px; color: var(--ink-dim);
    background: #0d1320; border: 1px solid var(--edge); border-radius: 3px;
    padding: 3px 8px; cursor: pointer; font-variant-numeric: tabular-nums;
  }
  .rbtn:hover { color: var(--cyan); border-color: var(--cyan); }
  .rbtn.on { color: var(--amber); border-color: var(--amber); }
  .rbtn:focus-visible { outline: 2px solid var(--cyan); outline-offset: 1px; }

  main { flex: 1; display: flex; min-height: 0; }

  /* The log, on the left, collapsed to a strip. */
  .log { display: flex; flex-shrink: 0; border-right: 1px solid var(--edge); background: var(--panel); }
  .log .tab {
    writing-mode: vertical-rl; text-orientation: mixed;
    padding: 14px 7px; border: none; background: transparent; cursor: pointer;
    font-family: var(--mono); font-size: 10px; letter-spacing: 0.18em; text-transform: uppercase;
    color: var(--ink-dim);
  }
  .log .tab:hover { color: var(--cyan); }
  .log.open .tab { color: var(--amber); }
  .log .tab:focus-visible { outline: 2px solid var(--cyan); outline-offset: -2px; }

  .logbody { width: 310px; overflow-y: auto; padding: 14px 16px 28px;
             border-left: 1px solid var(--edge); }
  .logbody h2.spaced { margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--edge); }
  .logbody h2 { margin: 0 0 8px; font-size: 11px; font-weight: 600; letter-spacing: 0.16em;
                text-transform: uppercase; color: var(--ink-dim); }
  .tickrow { display: flex; flex-wrap: wrap; gap: 4px 8px; align-items: baseline;
             margin: 14px 0 4px; padding-top: 6px; border-top: 1px solid var(--edge); }
  .tickrow .t { color: var(--amber); font-size: 11px; min-width: 16px; font-variant-numeric: tabular-nums; }
  .tickrow .v { font-size: 10.5px; color: var(--ink-dim); font-variant-numeric: tabular-nums; }
  .tickrow .q { color: var(--ink-faint); margin-right: 2px; }
  .logbody ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 3px; }
  .logbody li { font-size: 11.5px; line-height: 1.45; color: var(--ink-dim); }
  .logbody li.hit { color: var(--warn); }
  .logbody li.explosion { color: var(--amber); }
  .logbody .who { color: var(--cyan); margin-right: 6px; }
  .logbody .all { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--ink-dim); }

  .plot { position: relative; flex: 1; min-width: 0; overflow: hidden;
          background: radial-gradient(120% 90% at 50% 50%, #0e1526 0%, #080b12 72%); }
  svg { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }
  .world { touch-action: none; cursor: grab; }
  .world:active { cursor: grabbing; }
  .world.aiming { cursor: crosshair; }
  .text-layer { pointer-events: none; }

  .overlay-msg {
    position: absolute; inset: 0; margin: auto; height: fit-content; width: fit-content; max-width: 70%;
    text-align: center; color: var(--ink-dim); font-size: 13px; line-height: 1.6; z-index: 3;
  }
  .overlay-msg.err { color: var(--warn); }

  /* geometry */
  .grid { stroke: #16203a; }
  .grid.axis { stroke: #26375e; }
  .origin { fill: none; stroke: #3d5384; }
  .blast { fill-opacity: 0.13; stroke: #04070d; }
  .wreck { stroke: var(--warn); fill: none; stroke-linecap: round; opacity: 0.9; }
  .wreck-core { fill: #ffd2d6; }
  .track { fill: none; stroke: var(--ghost); opacity: 0.75; }
  .track.enemy { stroke: #6d3242; }
  .mark { fill: var(--cyan); opacity: 0.45; }
  .mark.enemy { fill: var(--warn); opacity: 0.4; }
  .blip { fill: var(--cyan); opacity: 0.75; }
  .blip.enemy { fill: var(--warn); opacity: 0.95; }
  .target-hit { fill: transparent; cursor: crosshair; }
  .ship { fill: var(--cyan); }
  .ship.own { fill: var(--amber); }
  .halo { fill: none; stroke: var(--cyan); opacity: 0.25; }
  .halo.own { stroke: var(--amber); opacity: 0.4; }
  .halo.sel { stroke: var(--amber); opacity: 0.9; }
  /* Your other ships plan in green, so their courses read as distinct from the one you are
     working on without competing with the amber of the selected ship. */
  .course { fill: none; stroke: #57d98a; opacity: 0.6; stroke-linejoin: round; }
  .course.sel { stroke: var(--amber); opacity: 1; }
  .course-dot { fill: #57d98a; opacity: 0.75; }
  /* The route already flown: same colour family as the plan, but thinner and quieter so past
     reads as past without breaking the line up. */
  .wake { fill: none; stroke: #57d98a; opacity: 0.4; }
  .wake.sel { stroke: var(--amber); opacity: 0.6; }
  .wake.ally { stroke: var(--cyan); opacity: 0.3; }
  .wake-dot { fill: #57d98a; opacity: 0.5; }
  .wake-dot.sel { fill: var(--amber); opacity: 0.75; }
  .wake-dot.ally { fill: var(--cyan); opacity: 0.4; }
  .grab { fill: transparent; cursor: grab; }
  .grab:active { cursor: grabbing; }
  .joint { fill: #0a0e17; stroke: var(--cyan); pointer-events: none; }
  .joint.limit { stroke: var(--warn); }
  .joint.cur { fill: var(--cyan); }
  /* Arcs and cones are decoration: they must never intercept a drag on a handle. */
  .arc { fill: var(--cyan); fill-opacity: 0.07; stroke: none; pointer-events: none; }
  .cone { fill: var(--cyan); fill-opacity: 0.07; stroke: var(--cyan); stroke-opacity: 0.32;
          pointer-events: none; }
  .cone.cur { fill-opacity: 0.11; stroke-opacity: 0.55; }
  /* Another ship's sweep is context, so it stays grey rather than joining the cyan. */
  .cone.other { fill: var(--ink-dim); fill-opacity: 0.05; stroke: var(--ink-dim);
                stroke-opacity: 0.24; }
  .ship-hit { fill: transparent; cursor: pointer; }
  .shot { stroke: #ff7b7b; opacity: 0.4; }
  .shot.cur { opacity: 1; }
  .shot.other { opacity: 0.22; }
  .beam { stroke: #ff7b7b; opacity: 0.3; stroke-dasharray: 6 4; }
  .beam.cur { opacity: 0.75; }
  .beam.other { opacity: 0.18; }
  .shot-grab { fill: transparent; cursor: grab; }
  .shot-grab:active { cursor: grabbing; }
  .shot-handle { fill: #0a0e17; stroke: #ff7b7b; pointer-events: none; }
  .shot-tip { fill: #ff7b7b; opacity: 0.55; pointer-events: none; }
  .shot-tip.other { opacity: 0.28; }

  /* text overlay */
  .label { font-family: var(--mono); dominant-baseline: middle; }
  .label.sel { fill: var(--amber); font-weight: 700; }
  .label.own { fill: var(--amber); opacity: 0.75; }
  .label.ally { fill: var(--cyan); }
  .label.enemy { fill: var(--warn); }
  .leader { stroke: var(--ink-faint); stroke-width: 1; }
  .glyph { font-family: var(--mono); fill: var(--cyan); opacity: 0.8; pointer-events: auto; }
  .glyph.enemy { fill: var(--warn); }
  .tick-label { font-family: var(--mono); fill: var(--cyan); opacity: 0.65;
                dominant-baseline: middle; }
  .grid-label { font-family: var(--mono); fill: var(--ink-faint); }
  .scalebar { stroke: var(--ink-faint); stroke-width: 1; }
  .cursor-label { font-family: var(--mono); fill: var(--ink-dim); font-variant-numeric: tabular-nums; }
  .shot-label { font-family: var(--mono); fill: #ff9d9d; opacity: 0.45; dominant-baseline: middle; }
  .shot-label.cur { opacity: 1; font-weight: 600; }
  .shot-label.other { opacity: 0.25; }

  .zoom { position: absolute; top: 12px; left: 12px; display: flex; gap: 6px; z-index: 4; }
  .zoom button {
    font-family: var(--mono); font-size: 12px; color: var(--ink);
    background: rgba(13, 19, 32, 0.85); border: 1px solid var(--edge);
    padding: 5px 10px; border-radius: 3px; cursor: pointer;
  }
  .zoom button:hover { border-color: var(--cyan); color: var(--cyan); }
  .zoom button:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }

  .panel { width: 340px; flex-shrink: 0; border-left: 1px solid var(--edge); background: var(--panel);
           display: flex; flex-direction: column; overflow-y: auto; }
  .panel section { padding: 16px 18px; border-bottom: 1px solid var(--edge); }
  .panel section.grow { flex: 1; }
  .panel h2 { margin: 0 0 10px; font-size: 11px; font-weight: 600; letter-spacing: 0.16em;
              text-transform: uppercase; color: var(--ink-dim); }
  .panel h2.spaced { margin-top: 20px; }

  /* Bars only where there is a numeric maximum: hull and battery. */
  .gauge { display: grid; grid-template-columns: 54px 1fr 72px; align-items: center;
           gap: 8px; margin-bottom: 6px; }
  .gk { font-size: 11px; color: var(--ink-dim); }
  .gbar { height: 5px; background: #0d1320; border: 1px solid var(--edge); border-radius: 3px;
          overflow: hidden; }
  .gbar i { display: block; height: 100%; background: var(--hull-ok, #57d98a); }
  .gbar i.power { background: var(--cyan); }
  .gbar i.low { background: var(--warn); }
  .gv { font-size: 11px; color: var(--ink); text-align: right; font-variant-numeric: tabular-nums; }

  .comp { display: grid; grid-template-columns: 54px 1fr; gap: 8px; margin-top: 8px; }
  .cn { font-size: 11px; color: var(--ink-dim); }
  .cs { display: flex; flex-wrap: wrap; gap: 4px 10px; }
  .pair { font-size: 11px; color: var(--ink); white-space: nowrap; }
  .pair.spent { color: var(--amber); }
  .pk { color: var(--ink-faint); margin-left: 4px; }

  .specs { display: grid; grid-template-columns: 88px 1fr; gap: 4px 10px; font-size: 11px; }
  .sk { color: var(--ink-faint); }
  .sv { color: var(--ink); font-variant-numeric: tabular-nums; }
  .pf { color: var(--ink-faint); }

  .hint { font-size: 12.5px; line-height: 1.55; margin: 0; }
  .sub-hint { margin-top: 10px; color: var(--ink-dim); font-size: 11.5px; }
  .note { font-size: 11.5px; color: var(--ink-dim); margin: 10px 0 0; line-height: 1.45; }

  .ships { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 3px; }
  .pick {
    width: 100%; display: flex; align-items: baseline; gap: 8px; text-align: left;
    font-family: var(--mono); font-size: 12.5px; color: var(--ink);
    background: #0d1320; border: 1px solid var(--edge); border-radius: 3px;
    padding: 6px 9px; cursor: pointer;
  }
  .pick:hover { border-color: var(--cyan); }
  .pick.on { border-color: var(--amber); color: var(--amber); }
  .pick.gone .nm { text-decoration: line-through; color: var(--ink-faint); }
  .pick:focus-visible { outline: 2px solid var(--cyan); outline-offset: 1px; }
  .pick .nm { flex: 1; }
  .pick .ty, .ally-row .ty { color: var(--ink-dim); font-size: 11px; }
  .pick .sp { font-variant-numeric: tabular-nums; }
  .ally-row { display: flex; gap: 8px; align-items: center; padding: 6px 9px; font-size: 12.5px;
              color: var(--cyan); opacity: 0.7; }
  .ally-row .nm { flex: 1; }

  /* Ready or not, per commander. Dim rather than red: not being ready yet is normal. */
  .lamp { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
          background: #33405f; }
  .lamp.lit { background: #79b894; box-shadow: 0 0 5px rgba(121, 184, 148, 0.6); }

  .weapons { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
  .weapons li { border: 1px solid var(--edge); border-radius: 3px; padding: 7px 9px; background: #0d1320; }
  .weapons li.armed { border-color: #ff7b7b; }
  .wrow { display: grid; grid-template-columns: 30px 74px 1fr; align-items: center;
          gap: 8px; font-size: 12.5px; }
  .wname { color: var(--hull); font-weight: 600; }
  .wammo { font-variant-numeric: tabular-nums; color: var(--cyan); font-size: 11.5px; }
  .wammo.out { color: var(--warn); }
  .wfire {
    font-family: var(--mono); font-size: 10.5px; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--ink); background: #121a2b;
    border: 1px solid var(--edge); border-radius: 3px; padding: 4px 0; cursor: pointer;
  }
  .wfire:hover:not(:disabled) { border-color: #ff7b7b; color: #ff7b7b; }
  .wfire:disabled { opacity: 0.35; cursor: not-allowed; }
  .wfire.on { border-color: #ff7b7b; color: #ff7b7b; }
  .worder { display: flex; align-items: center; gap: 10px; margin-top: 6px; flex-wrap: wrap; font-size: 12px; }
  .at { color: #ff9d9d; font-variant-numeric: tabular-nums; }
  .slider { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--ink-dim); padding: 0; }
  .slider input { width: 90px; accent-color: #ff7b7b; }
  .slider.aim { flex: 1 1 100%; }
  .slider.aim input { flex: 1; width: auto; }
  .slider b { color: var(--ink); font-variant-numeric: tabular-nums; }
  .slider select {
    flex: 1; min-width: 0; font: inherit; color: var(--ink); background: var(--panel);
    border: 1px solid var(--edge); border-radius: 3px; padding: 2px 4px;
  }
  .clear-shot {
    margin-left: auto; font-family: var(--mono); font-size: 10.5px; text-transform: uppercase;
    color: var(--ink-dim); background: transparent; border: 1px solid var(--edge);
    border-radius: 3px; padding: 2px 7px; cursor: pointer;
  }
  .clear-shot:hover { color: var(--warn); border-color: var(--warn); }

  .others { list-style: none; margin: 0; padding: 0; font-size: 12px; color: var(--ink-dim); }
  .others li { padding: 2px 0; }

  .legend { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px;
            font-size: 12px; color: var(--ink); }
  .legend li { display: flex; align-items: center; gap: 8px; }
  .sw { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .sw.own { background: var(--amber); opacity: 0.55; }
  .sw.sel-sw { background: var(--amber); }
  .sw.ally { background: var(--cyan); }
  .sw.enemy { background: var(--warn); }
  .sw.course-sw { background: #57d98a; }
  .sw.blast-sw { background: #ff9d4a; opacity: 0.35; border: 1px solid #04070d; }

  label { display: flex; align-items: center; gap: 8px; font-size: 12.5px; padding: 3px 0; cursor: pointer; }
  input[type="checkbox"] { accent-color: var(--amber); }

  table { width: 100%; border-collapse: collapse; font-size: 12.5px; font-variant-numeric: tabular-nums; }
  th, td { text-align: right; padding: 3px 6px; }
  th { font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--ink-dim);
       font-weight: 500; border-bottom: 1px solid var(--edge); }
  td.t, th.t { text-align: left; color: var(--ink-dim); }
  tr.idle td { color: var(--ink-faint); }
  tr.cur { background: #16203a; }
  .tick-pick {
    font-family: var(--mono); font-size: 12.5px; color: inherit; background: transparent;
    border: none; padding: 0 2px; cursor: pointer; text-decoration: underline dotted;
  }
  .tick-pick:hover { color: var(--cyan); }
  .fire-cell { color: #ff9d9d; text-align: left; font-size: 11px; }
  .turn { color: var(--cyan); }
  .accel { color: var(--amber); }
  .pinned { color: var(--warn); }
  .limits-line { margin: 8px 0 0; font-size: 11.5px; color: var(--ink-dim); }

  .tally { margin: 0 0 12px; font-size: 12px; color: var(--ink-dim); }
  .enemy-txt { color: var(--warn); }

  .fold summary {
    cursor: pointer; font-size: 11px; font-weight: 600; letter-spacing: 0.16em;
    text-transform: uppercase; color: var(--ink-dim); list-style: none;
  }
  .fold summary::-webkit-details-marker { display: none; }
  .fold summary::before { content: "▸ "; }
  .fold[open] summary::before { content: "▾ "; }
  .fold summary:hover { color: var(--ink); }
  .fold summary:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }
  .fold[open] summary { margin-bottom: 10px; }

  .buttons { display: flex; gap: 8px; margin-top: 14px; }
  .buttons button {
    font-family: var(--mono); font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase;
    border: 1px solid var(--edge); padding: 8px 12px; border-radius: 3px; cursor: pointer; flex: 1;
  }
  .ghost-btn { color: var(--ink); background: #0d1320; }
  .ghost-btn:hover:not(:disabled) { border-color: var(--cyan); color: var(--cyan); }
  .save { color: #08111e; background: var(--amber); border-color: var(--amber); font-weight: 600; }
  .save:hover:not(:disabled) { filter: brightness(1.1); }
  .buttons button:disabled { opacity: 0.4; cursor: not-allowed; }
  .buttons button:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }

  /* Muted, because these sit at rest most of the time. */
  .state { color: #b07a80; background: #1a1218; border-color: #4a2f34; }
  .state:hover:not(:disabled) { filter: brightness(1.25); }
  .state.on { color: #79b894; background: #121c17; border-color: #2f4a3a; }

  .savemsg { margin: 8px 0 0; font-size: 11.5px; line-height: 1.45; color: var(--cyan); word-break: break-word; }
  .savemsg.err { color: var(--warn); }

  @media (max-width: 760px) {
    main { flex-direction: column; }
    .panel { width: auto; border-left: none; border-top: 1px solid var(--edge); }
  }
</style>