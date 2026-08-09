import { clamp } from "./plan.js";

// Where the map is looking. North-up and world-fixed; `upp` is view units per screen pixel, so a
// marker sized `px * upp` never changes visual size while a real distance scales with the world.

const MIN_UPP = 0.05, MAX_UPP = 400;

// Grid spacing steps through 1/2/5 x 10^n, keeping lines roughly this far apart at any zoom.
const GRID_PX = 110;

function niceStep(raw) {
  const pow = 10 ** Math.floor(Math.log10(raw));
  const norm = raw / pow;
  return (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10) * pow;
}

export class Camera {
  cx = $state(0);
  cy = $state(0);
  upp = $state(2);
  // The plot's size in pixels, bound by whoever renders it.
  boxW = $state(0);
  boxH = $state(0);

  vb = $derived.by(() => {
    const w = Math.max(1, this.boxW) * this.upp;
    const h = Math.max(1, this.boxH) * this.upp;
    return { x: this.cx - w / 2, y: this.cy - h / 2, w, h };
  });

  // View coordinates to pixels within the plot, and back.
  sx = (vx) => (vx - this.vb.x) / this.upp;
  sy = (vy) => (vy - this.vb.y) / this.upp;
  toWorld = (px, py) => ({ x: this.vb.x + px * this.upp, y: -(this.vb.y + py * this.upp) });

  panByPixels(dxPx, dyPx) {
    this.cx -= dxPx * this.upp;
    this.cy -= dyPx * this.upp;
  }

  // Zoom leaving whatever sits under (px, py) where it is. The wheel, a pinch and the buttons
  // all come through here, so they cannot drift apart.
  zoomAt(px, py, factor) {
    const vxAt = this.vb.x + px * this.upp, vyAt = this.vb.y + py * this.upp;
    const upp = clamp(this.upp * factor, MIN_UPP, MAX_UPP);
    this.cx = vxAt - px * upp + (this.boxW * upp) / 2;
    this.cy = vyAt - py * upp + (this.boxH * upp) / 2;
    this.upp = upp;
  }

  zoomBy(factor) {
    this.zoomAt(this.boxW / 2, this.boxH / 2, factor);
  }

  centreOn(vx, vy) {
    this.cx = vx;
    this.cy = vy;
  }

  fitTo(points) {
    if (!points.length || !this.boxW || !this.boxH) return;
    const xs = points.map((p) => p.vx), ys = points.map((p) => p.vy);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    this.cx = (minX + maxX) / 2;
    this.cy = (minY + maxY) / 2;
    this.upp = clamp(Math.max(Math.max(maxX - minX, 50) / this.boxW,
                              Math.max(maxY - minY, 50) / this.boxH) * 1.15, MIN_UPP, MAX_UPP);
  }

  grid = $derived.by(() => {
    if (!this.boxW || !this.boxH) return { step: 100, xs: [], ys: [] };
    const step = niceStep(this.upp * GRID_PX);
    const xs = [], ys = [];
    for (let x = Math.ceil(this.vb.x / step) * step; x <= this.vb.x + this.vb.w; x += step) xs.push(x);
    for (let y = Math.ceil(this.vb.y / step) * step; y <= this.vb.y + this.vb.h; y += step) ys.push(y);
    return { step, xs, ys };
  });

  scaleBarPx = $derived(this.grid.step / this.upp);
}
