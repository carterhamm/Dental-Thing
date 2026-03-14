// Adapted from iOS 26.2+ Menu Morph — left-anchored variant

interface SpringCfg { omega: number; k: number; zeta: number }
export interface Sp { v: number; vel: number; t: number }

function springCfg(response: number, damping: number): SpringCfg {
  const omega = (2 * Math.PI) / response;
  return { omega, k: omega * omega, zeta: damping };
}

function stepSp(s: Sp, dt: number, c: SpringCfg): Sp {
  const d = s.v - s.t;
  const a = -c.k * d - 2 * c.zeta * c.omega * s.vel;
  return { v: s.v + s.vel * dt, vel: s.vel + a * dt, t: s.t };
}

function settled(s: Sp): boolean {
  return Math.abs(s.v - s.t) < 0.01 && Math.abs(s.vel) < 0.1;
}

const SP_SHAPE = springCfg(0.50, 0.82);
const SP_POS = springCfg(0.48, 0.48);
const SP_REV = springCfg(0.43, 0.70);

function keyLerp(keys: [number, number][], p: number): number {
  if (p <= keys[0][0]) return keys[0][1];
  if (p >= keys[keys.length - 1][0]) return keys[keys.length - 1][1];
  for (let i = 0; i < keys.length - 1; i++) {
    const [p0, v0] = keys[i];
    const [p1, v1] = keys[i + 1];
    if (p >= p0 && p <= p1) {
      const t = (p - p0) / (p1 - p0);
      const s = t * t * (3 - 2 * t);
      return v0 + (v1 - v0) * s;
    }
  }
  return keys[keys.length - 1][1];
}

export function morphPath(
  cx: number, cy: number, w: number, h: number, r: number,
): string {
  r = Math.min(r, w / 2, h / 2);
  const hw = w / 2, hh = h / 2;
  const L = cx - hw, R = cx + hw, T = cy - hh, B = cy + hh;
  const k = 0.5522847498;
  return `M${L + r},${T} L${R - r},${T}` +
    ` C${R - r + k * r},${T} ${R},${T + r - k * r} ${R},${T + r}` +
    ` L${R},${B - r}` +
    ` C${R},${B - r + k * r} ${R - r + k * r},${B} ${R - r},${B}` +
    ` L${L + r},${B}` +
    ` C${L + r - k * r},${B} ${L},${B - r + k * r} ${L},${B - r}` +
    ` L${L},${T + r}` +
    ` C${L},${T + r - k * r} ${L + r - k * r},${T} ${L + r},${T} Z`;
}

export interface MorphTarget {
  pillLeft: number;
  pillRight: number;
  pillTop: number;
  pillCx: number;
  pillCy: number;
  pillWidth: number;
  pillHeight: number;
  menuWidth: number;
  menuHeight: number;
  menuRadius: number;
}

export interface MorphState {
  width: number; height: number; cornerRadius: number;
  cx: number; cy: number;
  contentOpacity: number;
}

export interface AnimSprings {
  shape: Sp;
  pos: Sp;
  content: Sp;
  direction: 'forward' | 'reverse';
}

const DROP = 70;

export function createSprings(_target: MorphTarget, direction: 'forward' | 'reverse'): AnimSprings {
  if (direction === 'forward') {
    return {
      shape: { v: 0, vel: 2.2, t: 1 },
      pos: { v: 0, vel: 2.2, t: 1 },
      content: { v: 0, vel: 0, t: 0 },
      direction,
    };
  } else {
    return {
      shape: { v: 1, vel: -2, t: 0 },
      pos: { v: 1, vel: -2, t: 0 },
      content: { v: 1, vel: -3, t: 0 },
      direction,
    };
  }
}

export function tickSprings(s: AnimSprings, dt: number, _t: MorphTarget): boolean {
  if (s.direction === 'forward') {
    s.shape = stepSp(s.shape, dt, SP_SHAPE);
    s.pos = stepSp(s.pos, dt, SP_POS);
    s.content = stepSp(s.content, dt, SP_REV);
    if (s.shape.v > 0.75) s.content.t = 1;
  } else {
    s.shape = stepSp(s.shape, dt, SP_REV);
    s.pos = stepSp(s.pos, dt, SP_REV);
    s.content = stepSp(s.content, dt, SP_REV);
  }

  if (settled(s.shape) && settled(s.pos) && settled(s.content)) {
    s.shape.v = s.shape.t; s.shape.vel = 0;
    s.pos.v = s.pos.t; s.pos.vel = 0;
    s.content.v = s.content.t; s.content.vel = 0;
    return true;
  }
  return false;
}

export function readState(s: AnimSprings, t: MorphTarget): MorphState {
  const sp = Math.max(0, Math.min(1, s.shape.v));
  const pp = Math.max(-0.05, Math.min(1.15, s.pos.v));

  const circle = t.pillHeight;
  const vertW = t.menuWidth * 0.7;
  const vertH = t.menuHeight * 0.7;

  const width = keyLerp([
    [0.00, t.pillWidth],
    [0.18, circle],
    [0.38, circle],
    [0.62, vertW],
    [1.00, t.menuWidth],
  ], sp);

  const height = keyLerp([
    [0.00, t.pillHeight],
    [0.18, circle],
    [0.38, circle],
    [0.62, vertH],
    [1.00, t.menuHeight],
  ], sp);

  const dropTop = t.pillCy + DROP - circle / 2;
  const vertCy = dropTop + vertH / 2;
  const finalCy = t.pillTop + t.menuHeight / 2;

  const cy = keyLerp([
    [0.00, t.pillCy],
    [0.15, t.pillCy],
    [0.38, t.pillCy + DROP],
    [0.62, vertCy],
    [1.00, finalCy],
  ], pp);

  // Left-anchored: menu expands rightward from pill's left edge
  const pillLeft = t.pillCx - t.pillWidth / 2;
  const cx = keyLerp([
    [0.00, t.pillCx],
    [0.38, t.pillCx],
    [0.62, pillLeft + vertW / 2],
    [1.00, pillLeft + t.menuWidth / 2],
  ], sp);

  const maxRound = Math.min(width, height) / 2;
  const cr = keyLerp([
    [0.00, t.pillHeight / 2],
    [0.62, Math.min(vertW, vertH) / 2],
    [0.85, t.menuRadius],
    [1.00, t.menuRadius],
  ], sp);

  return {
    width: Math.max(1, width),
    height: Math.max(1, height),
    cornerRadius: Math.min(cr, maxRound),
    cx, cy,
    contentOpacity: Math.max(0, Math.min(1, s.content.v)),
  };
}
