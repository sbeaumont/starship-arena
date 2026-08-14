// The shapes an object in space is drawn as. Pure geometry, no Svelte and no DOM, so the map and
// the replay draw a starbase the same way.
//
// Sizes are screen pixels: `upp` (view units per pixel) turns them into world units, which is what
// keeps a marker the same size at any zoom. A real distance is never drawn through here.

export const SIZE = { Ship: 11, Starbase: 7.5, Beacon: 9, Missile: 5.5, Mine: 5 };

const rad = (d) => (d * Math.PI) / 180;
const pts = (arr) => arr.map((q) => q.join(",")).join(" ");

export function tri(vx, vy, headingDeg, rPx, upp) {
  const r = rPx * upp, h = rad(headingDeg);
  const p = (a, k) => [vx + Math.sin(a) * r * k, vy - Math.cos(a) * r * k];
  return pts([p(h, 1), p(h + 2.5, 0.62), p(h - 2.5, 0.62)]);
}

export function diamond(vx, vy, rPx, upp) {
  const r = rPx * upp;
  return pts([[vx, vy - r], [vx + r, vy], [vx, vy + r], [vx - r, vy]]);
}

export function square(vx, vy, rPx, upp) {
  const r = rPx * upp * 0.85;
  return pts([[vx - r, vy - r], [vx + r, vy - r], [vx + r, vy + r], [vx - r, vy + r]]);
}

// Six points, for something fixed that is worth flying to.
export function star(vx, vy, rPx, upp) {
  const r = rPx * upp;
  return pts(Array.from({ length: 12 }, (_, i) => {
    const a = rad(i * 30), k = i % 2 ? 0.42 : 1;
    return [vx + Math.sin(a) * r * k, vy - Math.cos(a) * r * k];
  }));
}

// A course of null is something whose heading is not known, which is a single sighting.
export function markerFor(category, vx, vy, course, upp) {
  const r = SIZE[category] ?? 5;
  if (category === "Starbase") return square(vx, vy, r, upp);
  if (category === "Beacon") return star(vx, vy, r, upp);
  if (category === "Mine") return diamond(vx, vy, r, upp);
  if (course === null) return diamond(vx, vy, r * 0.5, upp);
  return tri(vx, vy, course, r, upp);
}

// A ray burst, drawn where something died. World units: it stands for a place, not a control.
export function burst(x, y, r) {
  let d = "";
  for (let i = 0; i < 12; i++) {
    const a = (i * Math.PI) / 6;
    const inner = i % 2 ? r * 0.28 : r * 0.42;
    d += `M${x + Math.sin(a) * inner} ${y - Math.cos(a) * inner}`
       + `L${x + Math.sin(a) * r} ${y - Math.cos(a) * r}`;
  }
  return d;
}