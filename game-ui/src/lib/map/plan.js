// Orders as the map works with them: read out of command lines, simulated into a course, and
// written back. Pure functions, no Svelte and no DOM, so both shells share one reading of a plan.

export const N = 10; // ticks in a round

export const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
export const rad = (d) => (d * Math.PI) / 180;
export const normDelta = (d) => ((d + 180) % 360 + 360) % 360 - 180;

// World-fixed and north-up: the view is the world with y flipped.
export const w2v = (x, y) => ({ vx: x, vy: -y });

// Presentation rule: these categories are named on the map, everything else (missiles, mines,
// ...) is drawn as a small glyph. Categories come from the API.
export const NAMED = new Set(["Ship", "Starbase"]);

// A starbase carries weapons but cannot be given a course.
export const canMove = (s) => s.category_name === "Ship" && s.alive;

const MOVE_RE = /^\s*(\d+)\s*:\s*([RLA])\s*(-?\d+)\s*$/i;
const FIRE_RE = /^\s*(\d+)\s*:\s*(?:F|FIRE|SCAN|REP|REPLENISH)\s+(\S+)\s*(.*)$/i;
const COMP_RE = /^\s*(\d+)\s*:\s*([A-Za-z]+)\s+(\S+)\s*(.*)$/;

// Which order a component takes, by the collection its machine carries it in. Shields are
// boosted, ECM is powered; weapons are aimed on the map and have their own controls.
export const ORDER_VERB = { defense: "Boost", ecm: "Power" };

export const orderable = (ship) =>
  ship.components.filter((c) => ORDER_VERB[c.group] && c.inputs.length);

export function parseOrders(lines, ship) {
  const turn = Array(N + 1).fill(0), accel = Array(N + 1).fill(0);
  const fire = {}, comp = {}, other = [];
  // Recognised by the selector rather than by the verb, so the words a player may type stay the
  // server's business. Whatever they wrote is kept and written back unchanged.
  const takesOrders = new Set(orderable(ship).map((c) => c.name));
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
    const cr = text.match(COMP_RE);
    if (cr && Number(cr[1]) >= 1 && Number(cr[1]) <= N && takesOrders.has(cr[3])) {
      const t = Number(cr[1]);
      if (!comp[t]) comp[t] = {};
      comp[t][cr[3]] = { verb: cr[2], params: cr[4].split(/\s+/).filter(Boolean) };
      continue;
    }
    other.push(text);
  }
  return { turn, accel, fire, comp, other };
}

export function orderLines(o) {
  const rows = [];
  for (let t = 1; t <= N; t++) {
    if (o.turn[t]) rows.push([t, `${t}: ${o.turn[t] > 0 ? "R" : "L"}${Math.abs(o.turn[t])}`]);
    if (o.accel[t]) rows.push([t, `${t}: A${o.accel[t]}`]);
    for (const [wpn, params] of Object.entries(o.fire[t] ?? {})) {
      rows.push([t, `${t}: Fire ${wpn} ${params.join(" ")}`.trim()]);
    }
    for (const [name, c] of Object.entries(o.comp[t] ?? {})) {
      rows.push([t, `${t}: ${c.verb} ${name} ${c.params.join(" ")}`.trim()]);
    }
  }
  for (const line of o.other) {
    const m = line.match(/^\s*(\d+)\s*:/);
    rows.push([m ? Number(m[1]) : N + 1, line]);
  }
  return rows.sort((a, b) => a[0] - b[0]).map((r) => r[1]);
}

// The same forward simulation the engine runs, so the drawn course is the one that will happen.
export function simulate(s, o) {
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

// What the camera should frame: everything on the map, and where your ships are going, which
// matters as much as where they are.
export function framePoints(plan, chains) {
  const pts = [];
  for (const s of plan.ships) pts.push(w2v(s.x, s.y));
  for (const s of plan.ships) for (const t of s.track) pts.push(w2v(t.x, t.y));
  for (const c of plan.contacts) for (const t of c.track) pts.push(w2v(t.x, t.y));
  for (const chain of Object.values(chains)) for (const n of chain) pts.push(w2v(n.x, n.y));
  return pts;
}

// ===== What a weapon asks for. Every shape comes from the API's inputs; nothing is by name. =====

export const directionIndex = (weapon) => weapon.inputs.findIndex((i) => i.kind === "direction");

// The arc as a straight low..high range of relative angles, for a slider. An arc that wraps
// through dead ahead (270..90) becomes -90..90.
export function arcRange(weapon) {
  if (!weapon.firing_arc) return [-180, 180];
  const [lo, hi] = weapon.firing_arc;
  return lo > hi ? [lo - 360, hi] : [lo, hi];
}

// Angles arrive as -180..180, while an arc that does not pass through dead ahead runs 90..270.
// Move the angle to the turn of the circle nearest the arc, then hold it between the edges.
export function clampToArc(weapon, angle) {
  const [lo, hi] = arcRange(weapon);
  const mid = (lo + hi) / 2;
  const a = angle - 360 * Math.round((angle - mid) / 360);
  return Math.round(Math.min(hi, Math.max(lo, a)));
}

export function defaultDirection(weapon) {
  const [lo, hi] = arcRange(weapon);
  return Math.round((lo + hi) / 2);
}

// A weapon whose target is named rather than aimed, and not offered as a list, waits for
// something on the map to be picked.
export const needsATarget = (weapon) =>
  weapon.inputs.some((i) => i.kind === "object_name" && !i.choices);

// The starting parameters for a weapon armed without being aimed first.
export const defaultParams = (weapon) =>
  weapon.inputs.map((i) =>
    i.choices ? (i.choices[0] ?? "")
    : i.kind === "direction" ? String(defaultDirection(weapon))
    : String(Math.round(i.max ?? 0))
  );

// World units, for a scanner's arrow and the cone it sweeps, so both scale with the map and can
// be read against the grid. Ordnance is drawn the distance it really travels; a scan has no such
// figure, so this is simply an indicative length.
export const SCAN_REACH = 7;

// A weapon that takes a direction plus an angular width sweeps a cone. Its handle sets both at
// once: turning it aims the sweep, pulling it out narrows the cone, which reads the way the game
// behaves since a tighter sweep really does see further.
export const coneInput = (weapon) =>
  weapon.inputs.length > 1 && weapon.inputs[1].kind === "number_in_range" ? weapon.inputs[1] : null;

export function coneRadius(inp, width) {
  const tightness = clamp((inp.max - width) / (inp.max - inp.min), 0, 1);
  return SCAN_REACH * (1 + 2 * tightness);
}

export function coneWidthAt(inp, distance) {
  const pulled = clamp((distance - SCAN_REACH) / (2 * SCAN_REACH), 0, 1);
  return Math.round((inp.max - pulled * (inp.max - inp.min)) / 5) * 5;
}
