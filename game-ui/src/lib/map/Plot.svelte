<script>
  import {
    N, NAMED, SCENERY, canMove, clamp, rad, normDelta, w2v,
    directionIndex, clampToArc, coneInput, coneRadius, coneWidthAt, SCAN_REACH,
  } from "./plan.js";
  import { burst, markerFor, tri } from "./markers.js";

  // The map itself: two SVG layers and every gesture that reaches them. Geometry in world
  // coordinates, which pans and zooms; text and leader lines in screen pixels, which do not.
  //
  // `grabbable` is the whole of what one shell does differently from the other. Nothing in here
  // asks which shell it is in.
  let {
    planning, camera, layers, coarse = false,
    grabbable = { path: true, shots: true, ticks: true },
    children,
  } = $props();

  const plan = $derived(planning.plan);

  // Text sizes live here rather than in the CSS because the de-overlap maths needs them.
  const LABEL_PX = 12.5;
  const GLYPH_PX = 11;
  const CHAR_W = LABEL_PX * 0.6;
  const LINE_H = LABEL_PX + 3;

  // Screen px, for the controls rather than for distances: the radius the firing arc is drawn at,
  // and the handle length for the shot being planned.
  const FIRE_LEN = 36;
  const EDIT_LEN = 54;
  // World units, like a blast. The mark is the moment something was killed, not the wreck it
  // leaves: a wreck sits in space afterwards and is nothing this draws.
  const KILL_RADIUS = 20;

  // The API's symbols for the machine itself, as against one of its defence components. Breaching
  // a defence layer lets the blow through; breaching the hull is the end of the ship.
  const HULL = "hull";
  const MACHINE = new Set(["hull", "battery"]);

  // A finger is not a cursor. Every invisible hit target grows for one, which only works because
  // the shell has already said which of them are live.
  const HIT = $derived(coarse
    ? { ship: 24, node: 22, shot: 21, target: 24 }
    : { ship: 16, node: 13, shot: 11, target: 14 });

  const upp = $derived(camera.upp);
  const vb = $derived(camera.vb);

  // ===== What is on the map =====

  const contacts = $derived.by(() => {
    if (!plan) return [];
    return plan.contacts
      .filter((c) => {
        if (SCENERY.has(c.category_name)) return false;
        if (NAMED.has(c.category_name)) return true;
        return c.stance === "Friend" ? layers.friendlyOrdnance : layers.enemyOrdnance;
      })
      // Ships last. SVG paints in order and the aiming target rides with the blip, so ordnance
      // that went off on a ship would otherwise sit between you and the ship you want to shoot.
      .sort((a, b) => Number(NAMED.has(a.category_name)) - Number(NAMED.has(b.category_name)));
  });

  // Last seen before the round ended: it is either gone or out of range, and either way where it
  // is drawn is where it was, not where it is.
  const stale = (c) => c.track[c.track.length - 1].tick < N;

  const selected = $derived(plan?.ships.find((s) => s.name === planning.selected) ?? null);
  // Where you are now, and where the course you are drawing puts you on tick 10. The far one
  // moves as the course is dragged, which is the point of it.
  const scanRings = $derived.by(() => {
    if (!selected) return [];
    const c = planning.chain;
    return c?.length ? [c[0], c[c.length - 1]] : [{ x: selected.x, y: selected.y }];
  });

  // Scenery is drawn true to scale rather than as a marker, because a player plots around it.
  // The radius comes from the API, never from a number kept here.
  const terrain = $derived(plan ? plan.contacts.filter((c) => SCENERY.has(c.category_name)) : []);

  // ===== Geometry helpers (all marker sizes in screen px via upp) =====

  const trackPoints = (c) =>
    c.track.map((t) => { const v = w2v(t.x, t.y); return `${v.vx},${v.vy}`; }).join(" ");
  const lastOf = (c) => { const t = c.track[c.track.length - 1]; return w2v(t.x, t.y); };
  const viewPath = (nodes) =>
    nodes.map((n) => { const v = w2v(n.x, n.y); return `${v.vx},${v.vy}`; }).join(" ");

  function courseOf(c) {
    if (c.track.length < 2) return null;
    const a = c.track[c.track.length - 2], b = c.track[c.track.length - 1];
    const dx = b.x - a.x, dy = b.y - a.y;
    if (dx === 0 && dy === 0) return null;
    return (Math.atan2(dx, dy) * 180) / Math.PI;
  }

  // Along a heading by a length in screen pixels, or in world units.
  const along = (vx, vy, headingDeg, rPx) =>
    [vx + Math.sin(rad(headingDeg)) * rPx * upp, vy - Math.cos(rad(headingDeg)) * rPx * upp];
  const alongWorld = (vx, vy, headingDeg, len) =>
    [vx + Math.sin(rad(headingDeg)) * len, vy - Math.cos(rad(headingDeg)) * len];

  // The angular span a weapon covers, drawn at a node and rotated to the heading there. The
  // radius is in world units; a caller wanting a constant screen size passes px * upp.
  function wedge(vx, vy, headingDeg, arc, r) {
    const [lo, hi] = arc;
    const span = ((hi - lo) % 360 + 360) % 360;
    const a = alongWorld(vx, vy, headingDeg + lo, r);
    const b = alongWorld(vx, vy, headingDeg + lo + span, r);
    return `M ${vx},${vy} L ${a[0]},${a[1]} A ${r},${r} 0 ${span > 180 ? 1 : 0} 1 ${b[0]},${b[1]} Z`;
  }

  // A band across one side of something, centred on a bearing. The face that took a blow is the
  // one pointing at whoever landed it, so this needs nothing about the target's own heading.
  function arcAcross(vx, vy, bearing, span, r) {
    const a = alongWorld(vx, vy, bearing - span / 2, r);
    const b = alongWorld(vx, vy, bearing + span / 2, r);
    return `M ${a[0]},${a[1]} A ${r},${r} 0 0 1 ${b[0]},${b[1]}`;
  }


  // ===== Every planned shot the faction has on file, so a course and its firing read together
  //       whether or not that ship is the one being planned, and whoever commands it. =====

  const shots = $derived.by(() => {
    if (!plan) return [];
    const out = [];
    for (const ship of plan.ships) {
      const o = planning.ordersOf(ship), chain = planning.chains[ship.name];
      if (!o || !chain) continue;
      const byName = Object.fromEntries(ship.weapons.map((w) => [w.name, w]));
      const mine = ship.name === planning.selected;
      for (let t = 1; t <= N; t++) {
        for (const [name, params] of Object.entries(o.fire[t] ?? {})) {
          const weapon = byName[name];
          const node = chain[t];
          if (!weapon || !node) continue;
          // An arrow when the order was aimed, a line to what it named when it was not. Which of
          // the two is read off the weapon's inputs: a replenisher names a ship and points nowhere.
          const kind = directionIndex(weapon) >= 0 ? "direction" : weapon.inputs[0]?.kind;
          // Whatever it puts in space, or takes alongside, is named in the order: say that
          // rather than "SS".
          const label = weapon.inputs[0]?.choices ? params[0] : name;
          const nv = w2v(node.x, node.y);
          const cur = mine && t === planning.selectedTick;
          const key = `${ship.name}:${t}:${name}`;
          if (kind === "object_name") {
            // A contact is where it was last seen. One of the faction's own is where its plan
            // puts it at that tick, which is the picture its course is already drawn from.
            const c = plan.contacts.find((x) => x.name === params[0]);
            out.push({ key, ship: ship.name, mine, tick: t, weapon: name, label, kind, node, nv, cur,
                       target: c ? c.track[c.track.length - 1] : planning.chains[params[0]]?.[t] ?? null,
                       targetName: params[0] });
          } else {
            const angle = Number(params[directionIndex(weapon)]) || 0;
            const heading = node.heading + angle;
            // Everything that stands for a real distance is drawn in world units, so it can be
            // read against the grid. Only the handle you drag is sized on screen, because that is
            // a control rather than a distance - except a scanner's, whose distance is itself the
            // cone width and so has to sit where the width puts it.
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
              // A mine is launched at the ship's own speed and then slows to a stop, so its first
              // tick covers about that. Dropped at a standstill it stays put, and the arrowhead
              // alone marks the spot.
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

  // A weapon that takes a direction plus an angular width sweeps a cone. Show it as you set it,
  // so the sweep can be aimed rather than guessed.
  const cones = $derived.by(() => {
    if (!plan) return [];
    const out = [];
    for (const ship of plan.ships) {
      const o = planning.ordersOf(ship), chain = planning.chains[ship.name];
      if (!o || !chain) continue;
      const byName = Object.fromEntries(ship.weapons.map((w) => [w.name, w]));
      const mine = ship.name === planning.selected;
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
                     cur: mine && t === planning.selectedTick });
        }
      }
    }
    return out;
  });

  // ===== Text overlay =====

  const gridLabels = $derived.by(() => {
    if (!layers.grid) return [];
    const out = [];
    for (const x of camera.grid.xs) out.push({ key: `x${x}`, x: camera.sx(x), y: 13, text: `${Math.round(x)}`, mid: true });
    // Grid figures are world coordinates; view y runs the other way, hence the minus.
    for (const y of camera.grid.ys) out.push({ key: `y${y}`, x: 7, y: camera.sy(y) - 5, text: `${Math.round(-y)}`, mid: false });
    return out;
  });

  const labels = $derived.by(() => {
    if (!plan) return [];
    const items = [];
    for (const s of plan.ships) {
      const v = w2v(s.x, s.y);
      items.push({ key: `s:${s.name}`, x: camera.sx(v.vx), y: camera.sy(v.vy), text: s.name,
                   cls: s.owned ? (s.name === planning.selected ? "sel" : "own") : "ally" });
    }
    for (const c of contacts) {
      if (!NAMED.has(c.category_name)) continue;
      const v = lastOf(c);
      items.push({ key: `c:${c.name}`, x: camera.sx(v.vx), y: camera.sy(v.vy), text: c.name,
                   cls: c.stance === "Foe" ? "enemy" : "ally" });
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
      return { key: c.name, x: camera.sx(v.vx), y: camera.sy(v.vy), letter: c.type_name[0],
               enemy: c.stance === "Foe", title: `${c.name} · ${c.type_name}` };
    })
  );

  // Which tick is which node. A ship that comes to a stop parks every remaining tick on the same
  // spot, and a stack of joints otherwise reads as a single one, so a run of ticks sharing a
  // position is labelled as a range.
  const jointLabels = $derived.by(() => {
    if (!layers.paths || !planning.chain || !planning.ship || !canMove(planning.ship)) return [];
    const groups = [];
    for (const n of planning.chain.slice(1)) {
      const v = w2v(n.x, n.y);
      const last = groups[groups.length - 1];
      if (last && last.vx === v.vx && last.vy === v.vy) last.ticks.push(n.t);
      else groups.push({ vx: v.vx, vy: v.vy, ticks: [n.t] });
    }
    return groups.map((g) => ({
      key: `${g.ticks[0]}`,
      x: camera.sx(g.vx) + 9,
      y: camera.sy(g.vy) - 9,
      text: g.ticks.length === 1 ? `${g.ticks[0]}` : `${g.ticks[0]}–${g.ticks.at(-1)}`,
    }));
  });

  // Which handle is which weapon: name every planned shot, at its tip.
  const shotLabels = $derived.by(() => {
    if (!layers.fire) return [];
    return shots.map((s) => {
      if (s.kind === "object_name") {
        if (!s.target) return null;
        const tv = w2v(s.target.x, s.target.y);
        return { key: s.key, x: camera.sx((s.nv.vx + tv.vx) / 2), y: camera.sy((s.nv.vy + tv.vy) / 2),
                 text: s.label, cur: s.cur, mine: s.mine };
      }
      const tip = along(s.end[0], s.end[1], s.heading, 11);   // just beyond the arrow's point
      return { key: s.key, x: camera.sx(tip[0]), y: camera.sy(tip[1]), text: s.label, cur: s.cur, mine: s.mine };
    }).filter(Boolean);
  });

  // ===== Gestures =====
  // One pointer drags: the map, a course node, or a shot's handle, decided by what was pressed
  // and by what the shell says is grabbable. Two pointers pinch, and a pinch cancels whatever
  // one finger had started.

  let svgEl;
  const pointers = new Map();
  let gesture = "none";           // none | pan | node | shot | pinch
  let dragTick = null, dragShot = null;
  let grabDX = 0, grabDY = 0;     // world offset from the finger to the node it took hold of
  let grabDA = 0, grabDR = 0;     // the same for a shot handle: angle, and how far out it sits
  let lastX = 0, lastY = 0, downX = 0, downY = 0;
  let movedFar = false;
  let pendingShip = null;
  let pinch = null;
  let blocked = false;            // after a pinch, until every finger is off

  // A finger jitters on the way up, so what counts as holding still is not what it is for a mouse.
  const SLOP = $derived(coarse ? 9 : 3);

  let cursor = $state(null);      // world position under the pointer, for orientation
  let dragInfo = $state(null);    // what a drag is doing, since the tables are not always up

  function localOf(e) {
    const rect = svgEl.getBoundingClientRect();
    return { px: e.clientX - rect.left, py: e.clientY - rect.top };
  }
  function worldOf(e) {
    const { px, py } = localOf(e);
    return camera.toWorld(px, py);
  }
  function pinchNow() {
    const [a, b] = [...pointers.values()];
    const rect = svgEl.getBoundingClientRect();
    return { dist: Math.hypot(a.x - b.x, a.y - b.y),
             px: (a.x + b.x) / 2 - rect.left, py: (a.y + b.y) / 2 - rect.top };
  }

  // Capture, so a press on a handle is counted before the handle's own listener stops it.
  function trackDown(e) {
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.size !== 2) return;
    gesture = "pinch";
    pinch = pinchNow();
    dragTick = null; dragShot = null; pendingShip = null; dragInfo = null;
    movedFar = true;
  }

  function begin(e, what) {
    gesture = what;
    movedFar = false;
    lastX = downX = e.clientX;
    lastY = downY = e.clientY;
    svgEl.setPointerCapture(e.pointerId);
  }

  // Markers overlap all the time: ordnance goes off on the ship it killed, and a fleet flies in
  // formation. Whichever is painted on top is an accident of ordering and the nearest to a
  // fingertip is a guess, so when a tap covers more than one, the map asks which you meant.
  let choosing = $state(null);

  function under(e, items, reachPx) {
    const { px, py } = localOf(e);
    return items
      .map((it) => ({ ...it, d: Math.hypot(camera.sx(it.v.vx) - px, camera.sy(it.v.vy) - py) }))
      .filter((it) => it.d <= reachPx)
      .sort((a, b) => a.d - b.d);
  }

  // A row has to be worth a fingertip on the shell that has them.
  const ROW = $derived(coarse ? 44 : 34);

  function ask(e, hits, aiming) {
    const { px, py } = localOf(e);
    choosing = { px: Math.max(0, Math.min(px, camera.boxW - 170)),
                 py: Math.max(0, Math.min(py, camera.boxH - ROW * hits.length)),
                 hits, aiming };
  }

  function choose(name) {
    if (choosing.aiming) planning.pickTarget(name);
    else planning.selectShip(name);
    choosing = null;
  }

  function onDown(e) {
    if (gesture === "pinch" || blocked) return;
    choosing = null;
    if (plan && planning.aiming) {
      // The faction's own ships are aimable too: a base restocks one of them by name.
      const hits = under(e, [...contacts.map((c) => ({ name: c.name, note: c.type_name,
                                                       v: lastOf(c) })),
                             ...plan.ships.map((s) => ({ name: s.name, note: s.ship_type,
                                                         v: w2v(s.x, s.y) }))], HIT.target);
      if (hits.length > 1) return ask(e, hits, true);
      // No pan behind a pick: the tick panel you armed from would be cleared on the way up.
      if (hits.length === 1) return planning.pickTarget(hits[0].name);
    } else if (plan) {
      const hits = under(e, plan.ships.filter((s) => s.owned)
                              .map((s) => ({ name: s.name, note: s.ship_type,
                                             v: w2v(s.x, s.y) })), HIT.ship);
      if (hits.length > 1) return ask(e, hits, false);
      pendingShip = hits.length ? hits[0].name : null;
    }
    begin(e, "pan");
  }

  function nodeDown(t, e) {
    if (gesture === "pinch" || blocked) return;
    if (!planning.editable || (!grabbable.path && !grabbable.ticks)) return;
    e.stopPropagation();
    dragTick = t;
    // Grab where it was held rather than where the finger landed, so nothing jumps under a
    // fingertip that is wider than the node it took.
    const n = planning.chain[t], w = worldOf(e);
    grabDX = n.x - w.x; grabDY = n.y - w.y;
    begin(e, "node");
  }

  function shotDown(shot, e) {
    if (gesture === "pinch" || blocked) return;
    if (!planning.editable || !grabbable.shots || !shot.mine) return;
    e.stopPropagation();
    dragShot = shot;
    planning.selectedTick = shot.tick;   // taking hold of a shot switches planning to its tick
    const node = shot.node, w = worldOf(e);
    const bearing = (Math.atan2(w.x - node.x, w.y - node.y) * 180) / Math.PI;
    grabDA = normDelta(shot.heading - bearing);
    grabDR = Math.hypot(shot.end[0] - node.x, shot.end[1] + node.y)
           - Math.hypot(w.x - node.x, w.y - node.y);
    begin(e, "shot");
  }

  function dragNodeTo(e) {
    // A node you may tap but not drag still has to let the map through, or the course becomes a
    // strip of screen that swallows a pan.
    if (!grabbable.path) {
      camera.panByPixels(e.clientX - lastX, e.clientY - lastY);
      lastX = e.clientX; lastY = e.clientY;
      return;
    }
    const s = planning.ship, chain = planning.chain, o = planning.shipOrders;
    if (!s || !chain || !o) return;
    const prev = chain[dragTick - 1], w = worldOf(e);
    const dx = w.x + grabDX - prev.x, dy = w.y + grabDY - prev.y;
    const dh = clamp(normDelta((Math.atan2(dx, dy) * 180) / Math.PI - prev.heading),
                     -s.limits.max_turn, s.limits.max_turn);
    const dv = clamp(Math.hypot(dx, dy) - prev.speed, -s.limits.max_delta_v, s.limits.max_delta_v);
    const speed = clamp(prev.speed + dv, -s.limits.max_speed, s.limits.max_speed);
    o.turn[dragTick] = Math.round(dh);
    o.accel[dragTick] = Math.round(speed - prev.speed);
    planning.saveMsg = "";
    const turn = o.turn[dragTick], accel = o.accel[dragTick];
    dragInfo = `${dragTick} · ${turn ? (turn > 0 ? "R" : "L") + Math.abs(turn) : "ahead"}`
             + ` · A${accel > 0 ? "+" : ""}${accel} · speed ${Math.round(prev.speed + accel)}`;
  }

  function dragShotTo(e) {
    const ship = planning.ownShips.find((s) => s.name === dragShot.ship);
    const weapon = ship.weapons.find((x) => x.name === dragShot.weapon);
    const node = dragShot.node, w = worldOf(e);
    const bearing = (Math.atan2(w.x - node.x, w.y - node.y) * 180) / Math.PI;
    const angle = clampToArc(weapon, normDelta(bearing + grabDA - node.heading));
    const params = planning.orders[dragShot.ship].fire[dragShot.tick][dragShot.weapon];
    params[directionIndex(weapon)] = String(angle);
    // A scanner takes its cone width from how far out the handle is pulled.
    const inp = coneInput(weapon);
    let extra = "";
    if (inp) {
      const width = coneWidthAt(inp, Math.hypot(w.x - node.x, w.y - node.y) + grabDR);
      params[1] = String(width);
      extra = ` · ${width}° wide`;
    }
    planning.saveMsg = "";
    dragInfo = `${dragShot.weapon} · ${angle}°${extra}`;
  }

  function onMove(e) {
    const held = pointers.get(e.pointerId);
    if (held) { held.x = e.clientX; held.y = e.clientY; }
    if (!coarse) {
      const w = worldOf(e);
      cursor = { x: Math.round(w.x), y: Math.round(w.y) };
    }
    if (Math.hypot(e.clientX - downX, e.clientY - downY) > SLOP) movedFar = true;

    if (gesture === "pinch") {
      if (pointers.size < 2) return;
      const now = pinchNow();
      if (pinch && now.dist > 0 && pinch.dist > 0) {
        // Zoom about where the fingers were, then follow where they went, so the map does not
        // slide out from under a pinch that also moves.
        camera.zoomAt(pinch.px, pinch.py, pinch.dist / now.dist);
        camera.panByPixels(now.px - pinch.px, now.py - pinch.py);
      }
      pinch = now;
      return;
    }
    if (gesture === "shot") return dragShotTo(e);
    if (gesture === "node") return dragNodeTo(e);
    if (gesture === "pan") {
      camera.panByPixels(e.clientX - lastX, e.clientY - lastY);
      lastX = e.clientX; lastY = e.clientY;
    }
  }

  // A node pressed without really moving is a tap: show that tick's weapons. Tapping one of your
  // ships switches to planning it. A tap on empty space stops planning a tick, and cancels any
  // pending aim.
  function onUp(e) {
    pointers.delete(e.pointerId);
    const was = gesture;
    if (was !== "pinch" && !movedFar) {
      if (was === "node") {
        if (grabbable.ticks) planning.selectedTick = dragTick;
      } else if (pendingShip) {
        planning.selectShip(pendingShip);
      } else if (was === "pan") {
        planning.selectedTick = null;
        planning.aiming = null;
      }
    }
    if (was === "pinch") blocked = true;
    if (!pointers.size) blocked = false;
    gesture = "none";
    pinch = null;
    dragTick = null; dragShot = null; pendingShip = null; dragInfo = null;
    try { svgEl.releasePointerCapture(e.pointerId); } catch (_) { /* already gone */ }
  }

  // The wheel always zooms; panning is dragging.
  const WHEEL_ZOOM = 1.06; // per mouse notch
  const NOTCH_PX = 100;    // what a notch reports in pixel mode; Firefox reports 3 lines

  function onWheel(e) {
    e.preventDefault();
    // Normalised to pixels and capped at one notch, so mouse and trackpad both feel the same.
    const px = clamp(e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY, -NOTCH_PX, NOTCH_PX);
    const at = localOf(e);
    camera.zoomAt(at.px, at.py, Math.exp((px * Math.log(WHEEL_ZOOM)) / NOTCH_PX));
  }
</script>

<div class="plot" bind:clientWidth={camera.boxW} bind:clientHeight={camera.boxH}>
  {#if planning.loading}
    <p class="overlay-msg">Loading {planning.player}'s tactical picture…</p>
  {:else if planning.error}
    <p class="overlay-msg err">Couldn't reach the API: {planning.error}</p>
  {/if}

  <!-- Layer 1: geometry, in world coordinates. Pans and zooms. -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <svg bind:this={svgEl} class="world" class:aiming={planning.aiming}
       viewBox={`${vb.x} ${vb.y} ${vb.w} ${vb.h}`} preserveAspectRatio="none"
       role="img" aria-label="Faction tactical map. Drag to pan, pinch or scroll to zoom."
       onpointerdowncapture={trackDown}
       onpointerdown={onDown} onpointermove={onMove} onpointerup={onUp}
       onpointercancel={onUp} onwheel={onWheel} onpointerleave={() => (cursor = null)}>
    <!-- Terrain first, so everything else is read against it rather than through it. -->
    {#each terrain as body (body.name)}
      {@const v = lastOf(body)}
      <circle class="body" cx={v.vx} cy={v.vy} r={body.radius} stroke-width={upp} />
    {/each}

    {#if layers.grid}
      {#each camera.grid.xs as x (x)}
        <line class="grid" class:axis={x === 0} x1={x} y1={vb.y} x2={x} y2={vb.y + vb.h}
              stroke-width={upp} />
      {/each}
      {#each camera.grid.ys as y (y)}
        <line class="grid" class:axis={y === 0} x1={vb.x} y1={y} x2={vb.x + vb.w} y2={y}
              stroke-width={upp} />
      {/each}
      <circle class="origin" cx="0" cy="0" r={6 * upp} stroke-width={1.2 * upp} />
    {/if}

    {#if plan}
      <!-- How far the selected ship notices things, here and at the end of the course. -->
      {#if layers.scan && selected?.scan_range}
        {#each scanRings as p, i (i)}
          {@const v = w2v(p.x, p.y)}
          <circle class="scanring" class:from={i === 0} cx={v.vx} cy={v.vy}
                  r={selected.scan_range} stroke-width={upp}
                  stroke-dasharray="{6 * upp} {8 * upp}" />
        {/each}
      {/if}

      {#if layers.explosions}
        {#each plan.explosions as e (`${e.tick}:${e.x}:${e.y}:${e.radius}`)}
          {@const v = w2v(e.x, e.y)}
          <circle class="blast {e.damage_type.toLowerCase()}" cx={v.vx} cy={v.vy} r={e.radius}
                  stroke-width={upp} />
        {/each}
      {/if}

      {#each plan.ships.filter((s) => !s.alive && s.track.length) as s (s.name)}
        {@const last = s.track[s.track.length - 1]}
        {@const v = w2v(last.x, last.y)}
        <path class="kill" d={burst(v.vx, v.vy, KILL_RADIUS)} stroke-width={1.4 * upp} />
        <circle class="kill-core" cx={v.vx} cy={v.vy} r={KILL_RADIUS * 0.18} />
      {/each}

      <!-- What your own blows did: the gap each one crossed, then what it did where it landed. -->
      {#if layers.hits}
        {#each plan.beams as bm (`${bm.tick}:${bm.x1},${bm.y1}:${bm.x2},${bm.y2}`)}
          {@const from = w2v(bm.x1, bm.y1)}
          {@const to = w2v(bm.x2, bm.y2)}
          <line class="beam" x1={from.vx} y1={from.vy} x2={to.vx} y2={to.vy}
                stroke-width={1.2 * upp} />
        {/each}
        {#each plan.effects as f (`${f.tick}:${f.target}:${f.part}:${f.outcome}`)}
          {@const v = w2v(f.x, f.y)}
          {#if f.outcome === "Breached" && f.part === HULL}
            <path class="kill" d={burst(v.vx, v.vy, KILL_RADIUS)} stroke-width={1.4 * upp} />
            <circle class="kill-core" cx={v.vx} cy={v.vy} r={KILL_RADIUS * 0.18} />
          {:else if f.outcome === "Breached"}
            <path class="breach" d={arcAcross(v.vx, v.vy, f.bearing, 90, 15 * upp)}
                  stroke-width={2.6 * upp} />
          {:else if f.outcome === "Damaged" && MACHINE.has(f.part)}
            <circle class="struck" cx={v.vx} cy={v.vy} r={12 * upp} stroke-width={1.6 * upp} />
          {/if}
        {/each}
      {/if}

      {#each contacts as c (c.name)}
        {#if layers.tracks && c.track.length > 1}
          <polyline class="track" class:enemy={c.stance === "Foe"}
                    points={trackPoints(c)} stroke-width={1.2 * upp} />
          {#each c.track.slice(0, -1) as t (t.tick)}
            {@const v = w2v(t.x, t.y)}
            <circle class="mark" class:enemy={c.stance === "Foe"} cx={v.vx} cy={v.vy} r={1.6 * upp} />
          {/each}
        {/if}
        {@const v = lastOf(c)}
        <polygon class="blip" class:enemy={c.stance === "Foe"} class:stale={stale(c)}
                 points={markerFor(c.category_name, v.vx, v.vy, courseOf(c), upp)} />
        {#if planning.aiming}
          <!-- The reach of a tap, so the cursor says what is aimable. Which one you meant is
               settled in onDown, where every candidate under the pointer is known. -->
          <circle class="target-hit" cx={v.vx} cy={v.vy} r={HIT.target * upp} />
        {/if}
      {/each}

      <!-- Where the faction's ships actually went during the round. Dashed, to read as past
           rather than plan, and joining the ship where the planned course starts. -->
      {#if layers.tracks}
        {#each plan.ships.filter((s) => s.track.some((t) => t.x !== s.track[0].x || t.y !== s.track[0].y)) as s (s.name)}
          <polyline class="wake" class:sel={s.name === planning.selected} class:ally={!s.owned}
                    points={s.track.map((t) => { const v = w2v(t.x, t.y); return `${v.vx},${v.vy}`; }).join(" ")}
                    stroke-width={1.4 * upp} />
          {#each s.track.slice(0, -1) as t (t.tick)}
            {@const v = w2v(t.x, t.y)}
            <circle class="wake-dot" class:sel={s.name === planning.selected} class:ally={!s.owned}
                    cx={v.vx} cy={v.vy} r={1.8 * upp} />
          {/each}
        {/each}
      {/if}

      {#if layers.paths}
        {#each plan.ships.filter(canMove) as s (s.name)}
          {#if planning.chains[s.name]}
            {@const isSel = s.name === planning.selected}
            <polyline class="course" class:sel={isSel} class:ally={!s.owned}
                      points={viewPath(planning.chains[s.name])} stroke-width={2 * upp} />
            {#if !isSel}
              <!-- Where each tick lands, so another ship's course can be read at a glance
                   without giving it draggable handles. -->
              {#each planning.chains[s.name].slice(1) as n (n.t)}
                {@const v = w2v(n.x, n.y)}
                <circle class="course-dot" class:ally={!s.owned} cx={v.vx} cy={v.vy} r={2.4 * upp} />
              {/each}
            {/if}
          {/if}
        {/each}
      {/if}

      {#each plan.ships as s (s.name)}
        {@const v = w2v(s.x, s.y)}
        <circle class="halo" class:own={s.owned} class:sel={s.name === planning.selected}
                cx={v.vx} cy={v.vy} r={18 * upp} stroke-width={upp} />
        <polygon class="ship" class:own={s.owned}
                 points={markerFor(s.category_name, v.vx, v.vy, s.heading, upp)} />
        {#if planning.aiming}
          <circle class="target-hit" cx={v.vx} cy={v.vy} r={HIT.target * upp} />
        {:else if s.owned}
          <circle class="ship-hit" cx={v.vx} cy={v.vy} r={HIT.ship * upp} />
        {/if}
      {/each}

      <!-- Scan cones, behind everything else. -->
      {#each cones as c (c.key)}
        {#if c.width >= 360}
          <circle class="cone" class:cur={c.cur} class:other={!c.mine}
                  cx={c.nv.vx} cy={c.nv.vy} r={c.r} stroke-width={upp} />
        {:else}
          <path class="cone" class:cur={c.cur} class:other={!c.mine} stroke-width={upp}
                d={wedge(c.nv.vx, c.nv.vy, c.heading,
                         [c.dir - c.width / 2, c.dir + c.width / 2], c.r)} />
        {/if}
      {/each}

      <!-- Arcs of the weapons ordered at the tick being planned. Drawn before the shots so they
           sit behind them, and they never take the pointer. -->
      {#if planning.selectedTick && planning.ship && planning.chain?.[planning.selectedTick]}
        {@const node = planning.chain[planning.selectedTick]}
        {@const nv = w2v(node.x, node.y)}
        {#each planning.ship.weapons.filter((w) => w.firing_arc && planning.orderAt(planning.selectedTick, w.name)) as w (w.name)}
          <path class="arc" d={wedge(nv.vx, nv.vy, node.heading, w.firing_arc, (FIRE_LEN + 8) * upp)} />
        {/each}
      {/if}

      <!-- Planned shots: a branch off the node they are fired from. Shots at other ticks stay
           quiet - a small arrowhead - so the tick being planned stands out. -->
      {#if layers.fire}
        {#each shots as sh (sh.key)}
          {#if sh.kind === "object_name"}
            {#if sh.target}
              {@const tv = w2v(sh.target.x, sh.target.y)}
              <line class="shot-line" class:cur={sh.cur} class:other={!sh.mine}
                    x1={sh.nv.vx} y1={sh.nv.vy} x2={tv.vx} y2={tv.vy}
                    stroke-width={(sh.cur ? 1.6 : 1.1) * upp} />
            {/if}
          {:else}
            <line class="shot" class:cur={sh.cur} class:other={!sh.mine}
                  x1={sh.nv.vx} y1={sh.nv.vy} x2={sh.end[0]} y2={sh.end[1]}
                  stroke-width={(sh.cur ? 1.8 : 1.1) * upp} />
            {#if sh.mine && grabbable.shots}
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <circle class="shot-grab" cx={sh.end[0]} cy={sh.end[1]} r={HIT.shot * upp}
                      onpointerdown={(e) => shotDown(sh, e)} />
            {/if}
            {#if sh.cur}
              <circle class="shot-handle" cx={sh.end[0]} cy={sh.end[1]} r={4.5 * upp}
                      stroke-width={2 * upp} />
            {:else}
              <polygon class="shot-tip" class:other={!sh.mine}
                       points={tri(sh.end[0], sh.end[1], sh.heading, 4, upp)} />
            {/if}
          {/if}
        {/each}
      {/if}

      <!-- Draggable joints, only for the ship being planned. -->
      <!-- Back to front, so tick 1 ends up on top. At a standstill every node sits on the ship,
           and the one you grab should be the first tick: giving it speed pushes all the later
           nodes outwards at once, instead of having to drag each in turn. -->
      {#if layers.paths && planning.chain && planning.ship && canMove(planning.ship)}
        {#each planning.chain.slice(1).reverse() as n (n.t)}
          {@const v = w2v(n.x, n.y)}
          {#if planning.editable && (grabbable.path || grabbable.ticks)}
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <!-- pointer-only drag handle; keyboard planning is a later feature -->
            <circle class="grab" class:tap-only={!grabbable.path} cx={v.vx} cy={v.vy}
                    r={HIT.node * upp} onpointerdown={(e) => nodeDown(n.t, e)} />
          {/if}
          <circle class="joint" class:limit={n.atLimit} class:cur={n.t === planning.selectedTick}
                  cx={v.vx} cy={v.vy} r={5 * upp} stroke-width={2 * upp} />
        {/each}
      {/if}
    {/if}
  </svg>

  <!-- Layer 2: all text, in screen pixels. Immune to zoom by construction. -->
  <svg class="text-layer" viewBox={`0 0 ${Math.max(1, camera.boxW)} ${Math.max(1, camera.boxH)}`}
       preserveAspectRatio="none" aria-hidden="true">
    {#each gridLabels as g (g.key)}
      <text class="grid-label" x={g.x} y={g.y} font-size={GLYPH_PX}
            text-anchor={g.mid ? "middle" : "start"}>{g.text}</text>
    {/each}
    {#if layers.grid && camera.boxH}
      <line class="scalebar" x1="14" y1={camera.boxH - 18} x2={14 + camera.scaleBarPx} y2={camera.boxH - 18} />
      <line class="scalebar" x1="14" y1={camera.boxH - 22} x2="14" y2={camera.boxH - 14} />
      <line class="scalebar" x1={14 + camera.scaleBarPx} y1={camera.boxH - 22} x2={14 + camera.scaleBarPx} y2={camera.boxH - 14} />
      <text class="grid-label" x={14 + camera.scaleBarPx / 2} y={camera.boxH - 26}
            font-size={GLYPH_PX} text-anchor="middle">{camera.grid.step}</text>
    {/if}
    {#if cursor}
      <text class="cursor-label" x={Math.max(1, camera.boxW) - 12} y={Math.max(1, camera.boxH) - 14}
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

  {#if choosing}
    <div class="pickone" style="left: {choosing.px}px; top: {choosing.py}px; --row: {ROW}px;">
      {#each choosing.hits as h (h.name)}
        <button type="button" onclick={() => choose(h.name)}>
          {h.name}<span>{h.note}</span>
        </button>
      {/each}
    </div>
  {/if}

  <!-- What the drag is doing, because your hand is over the thing it is doing it to. -->
  {#if dragInfo}<p class="readout">{dragInfo}</p>{/if}

  {@render children?.()}
</div>

<style>
  /* A finger anywhere on the map is the map's, never the browser's, so the whole box says so
     rather than only the layer that happens to be hit. */
  .plot { position: relative; flex: 1; min-width: 0; min-height: 0; overflow: hidden;
          touch-action: none; overscroll-behavior: none;
          background: radial-gradient(120% 90% at 50% 50%, #0e1526 0%, #080b12 72%); }
  svg { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }
  .world { touch-action: none; cursor: grab; -webkit-user-select: none; user-select: none;
           -webkit-touch-callout: none; }
  .world:active { cursor: grabbing; }
  .world.aiming { cursor: crosshair; }
  .text-layer { pointer-events: none; }

  .overlay-msg {
    position: absolute; inset: 0; margin: auto; height: fit-content; width: fit-content; max-width: 70%;
    text-align: center; color: var(--ink-dim); font-size: 13px; line-height: 1.6; z-index: 3;
  }
  .overlay-msg.err { color: var(--warn); }

  .pickone {
    position: absolute; z-index: 6; display: flex; flex-direction: column;
    background: rgba(10, 14, 23, 0.96); border: 1px solid var(--amber); border-radius: 3px;
    overflow: hidden; min-width: 160px; max-width: 70vw;
  }
  .pickone button {
    display: flex; align-items: center; gap: 8px; text-align: left; cursor: pointer;
    font-family: var(--mono); font-size: 12px; color: var(--ink);
    background: transparent; border: none; border-bottom: 1px solid var(--edge);
    padding: 7px 10px; min-height: var(--row);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .pickone button:last-child { border-bottom: none; }
  .pickone button:hover { background: #16203a; color: var(--amber); }
  .pickone span { margin-left: auto; font-size: 11px; color: var(--ink-faint); }

  .readout {
    position: absolute; top: 10px; left: 50%; transform: translateX(-50%); margin: 0;
    padding: 5px 12px; border-radius: 3px; z-index: 5; pointer-events: none;
    background: rgba(10, 14, 23, 0.9); border: 1px solid var(--amber); color: var(--amber);
    font-size: 12px; letter-spacing: 0.06em; white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }

  /* geometry */
  .grid { stroke: #16203a; }
  .grid.axis { stroke: #26375e; }
  .origin { fill: none; stroke: #3d5384; }
  /* A blast's colour answers what kind of harm it carried, and nothing else. A type this has
     never heard of is drawn as an ordinary explosion rather than not drawn at all. */
  .blast { fill: var(--hit); fill-opacity: 0.13; stroke: #04070d; }
  .blast.nanocyte { fill: var(--nanocyte); }
  .blast.emp { fill: var(--emp); }
  /* Terrain is something to fly around, not something to read. Muted on purpose. */
  .body { fill: #1a2130; stroke: #2b3648; }
  .kill { stroke: var(--hit); fill: none; stroke-linecap: round; opacity: 0.9; }
  .kill-core { fill: var(--kill); }
  .breach { stroke: var(--hit); fill: none; stroke-linecap: round; opacity: 0.95; }
  .struck { stroke: var(--hit); fill: none; opacity: 0.55; }
  .track { fill: none; stroke: var(--ghost); opacity: 0.75; }
  .track.enemy { stroke: var(--foe); opacity: 0.3; }
  .mark { fill: var(--cyan); opacity: 0.45; }
  .mark.enemy { fill: var(--foe); opacity: 0.4; }
  .blip { fill: var(--cyan); opacity: 0.75; }
  .blip.enemy { fill: var(--foe); opacity: 0.95; }
  .blip.stale { opacity: 0.35; }

  .scanring { fill: none; stroke: var(--cyan); opacity: 0.3; }
  .scanring.from { opacity: 0.15; }
  .ship { fill: var(--cyan); }
  .ship.own { fill: var(--amber); }
  .halo { fill: none; stroke: var(--cyan); opacity: 0.25; }
  .halo.own { stroke: var(--amber); opacity: 0.4; }
  .halo.sel { stroke: var(--amber); opacity: 0.9; }
  /* A course of yours already laid in, so it reads as distinct from the one you are working
     on without competing with its amber. The ship itself stays amber either way. */
  .course { fill: none; stroke: var(--laid); opacity: 0.6; stroke-linejoin: round; }
  .course.sel { stroke: var(--amber); opacity: 1; }
  .course-dot { fill: var(--laid); opacity: 0.75; }
  /* A faction mate's plan is drawn in the cyan they are, so whose course it is reads off the
     colour rather than off the labels. */
  .course.ally { stroke: var(--cyan); opacity: 0.45; }
  .course-dot.ally { fill: var(--cyan); opacity: 0.55; }
  /* The route already flown: same colour family as the plan, but thinner and quieter so past
     reads as past without breaking the line up. */
  .wake { fill: none; stroke: var(--laid); opacity: 0.4; }
  .wake.sel { stroke: var(--amber); opacity: 0.6; }
  .wake.ally { stroke: var(--cyan); opacity: 0.3; }
  .wake-dot { fill: var(--laid); opacity: 0.5; }
  .wake-dot.sel { fill: var(--amber); opacity: 0.75; }
  .wake-dot.ally { fill: var(--cyan); opacity: 0.4; }
  .grab { fill: transparent; cursor: grab; }
  .grab:active { cursor: grabbing; }
  .grab.tap-only { cursor: pointer; }
  .joint { fill: var(--bg); stroke: var(--cyan); pointer-events: none; }
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
  .target-hit { fill: transparent; cursor: crosshair; }
  .shot { stroke: var(--beam); opacity: 0.4; }
  .shot.cur { opacity: 1; }
  .shot.other { opacity: 0.22; }
  /* A beam that was fired, against the dashed line of a shot that is only planned. */
  .beam { stroke: var(--beam); opacity: 0.6; }
  .shot-line { stroke: var(--beam); opacity: 0.3; stroke-dasharray: 6 4; }
  .shot-line.cur { opacity: 0.75; }
  .shot-line.other { opacity: 0.18; }
  .shot-grab { fill: transparent; cursor: grab; }
  .shot-grab:active { cursor: grabbing; }
  .shot-handle { fill: var(--bg); stroke: var(--beam); pointer-events: none; }
  .shot-tip { fill: var(--beam); opacity: 0.55; pointer-events: none; }
  .shot-tip.other { opacity: 0.28; }

  /* text overlay */
  .label { font-family: var(--mono); dominant-baseline: middle; }
  .label.sel { fill: var(--amber); font-weight: 700; }
  .label.own { fill: var(--amber); opacity: 0.75; }
  .label.ally { fill: var(--cyan); }
  .label.enemy { fill: var(--foe); }
  .leader { stroke: var(--ink-faint); stroke-width: 1; }
  .glyph { font-family: var(--mono); fill: var(--cyan); opacity: 0.8; pointer-events: auto; }
  .glyph.enemy { fill: var(--foe); }
  .tick-label { font-family: var(--mono); fill: var(--cyan); opacity: 0.65;
                dominant-baseline: middle; }
  .grid-label { font-family: var(--mono); fill: var(--ink-faint); }
  .scalebar { stroke: var(--ink-faint); stroke-width: 1; }
  .cursor-label { font-family: var(--mono); fill: var(--ink-dim); font-variant-numeric: tabular-nums; }
  .shot-label { font-family: var(--mono); fill: var(--beam); opacity: 0.45; dominant-baseline: middle; }
  .shot-label.cur { opacity: 1; font-weight: 600; }
  .shot-label.other { opacity: 0.25; }
</style>
