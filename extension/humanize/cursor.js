// Cursor trajectory generation: the path a hand takes between two points.
//
// Pure geometry + timing — no browser APIs. Everything here returns plain
// {x, y, ms} steps for the executor to dispatch.
//
// The properties being modelled, and why each matters:
//   - curvature      a hand does not travel in a straight line
//   - ballistic speed accelerate, then decelerate into the target (Fitts)
//   - overshoot      fast moves often pass the target and correct back
//   - endpoint spread you do not land on the same pixel twice, or dead-centre
// The invariant across all of it: the final point is always INSIDE the target,
// so randomisation never changes the outcome of the action.

import { clamp } from "./rng.js";

/** Cubic Bézier evaluation. */
function bezier(p0, p1, p2, p3, t) {
  const u = 1 - t;
  const a = u * u * u, b = 3 * u * u * t, c = 3 * u * t * t, d = t * t * t;
  return {
    x: a * p0.x + b * p1.x + c * p2.x + d * p3.x,
    y: a * p0.y + b * p1.y + c * p2.y + d * p3.y
  };
}

/** Ease-in-out — the ballistic accelerate/decelerate profile. */
function easeInOut(t) {
  return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
}

export function distance(a, b) {
  return Math.hypot(b.x - a.x, b.y - a.y);
}

/**
 * Pick the point to actually aim at inside an element's box. Gaussian around
 * a slightly off-centre spot, clamped well inside the edges so the click can
 * never miss — the "not the same pixel twice" property without the risk.
 */
export function sampleInBox(rect, rng, persona = { steadiness: 1 }) {
  if (!rect || !(rect.width > 0) || !(rect.height > 0)) return null;
  const cx = rect.x + rect.width / 2;
  const cy = rect.y + rect.height / 2;
  // Spread scales with the element but is capped: big targets get a human
  // amount of scatter, tiny ones stay tight enough to stay inside.
  const sdx = Math.min(rect.width / 5, 14) * persona.steadiness;
  const sdy = Math.min(rect.height / 5, 10) * persona.steadiness;
  // Keep a margin off the edge: never click the 1px border of a control.
  const mx = Math.min(rect.width * 0.32, 6);
  const my = Math.min(rect.height * 0.32, 5);
  return {
    x: Math.round(clamp(rng.gauss(cx, sdx), rect.x + mx, rect.x + rect.width - mx)),
    y: Math.round(clamp(rng.gauss(cy, sdy), rect.y + my, rect.y + rect.height - my))
  };
}

/**
 * Fitts's law: movement time grows with distance and shrinks with target
 * size. Gives long hauls a realistic duration instead of a fixed one.
 */
function moveDurationMs(dist, targetSize, rng, persona) {
  const w = clamp(targetSize || 24, 8, 260);
  const base = 90 + 105 * Math.log2(1 + dist / w);
  return clamp(rng.logNormal(base, 1.22) * persona.speed, 45, 1500);
}

/**
 * The trajectory: a curved, variably-sampled, accelerate/decelerate path from
 * `from` to `to`, optionally overshooting and correcting back.
 * Returns [{x, y, ms}] where ms is the delay BEFORE that point.
 */
export function planPath(from, to, rng, persona, opts = {}) {
  const dist = distance(from, to);
  const steps = [];
  if (dist < 1.5) return steps; // already there

  const targetSize = opts.targetSize || 24;
  const totalMs = moveDurationMs(dist, targetSize, rng, persona);

  // Point count scales with distance but stays bounded: enough samples to look
  // continuous, few enough that a long move is not thousands of CDP events.
  const n = Math.round(clamp(dist / rng.uniform(9, 22), 6, 46));

  // Control points offset perpendicular to the line — this is the curvature.
  // Sign is random, so paths bow either way; magnitude scales with distance.
  const dx = to.x - from.x, dy = to.y - from.y;
  const px = -dy / (dist || 1), py = dx / (dist || 1);
  const bow = clamp(dist * rng.uniform(0.05, 0.22), 4, 130) * (rng.chance(0.5) ? 1 : -1);
  const c1 = {
    x: from.x + dx * rng.uniform(0.15, 0.42) + px * bow * rng.uniform(0.4, 1),
    y: from.y + dy * rng.uniform(0.15, 0.42) + py * bow * rng.uniform(0.4, 1)
  };
  const c2 = {
    x: from.x + dx * rng.uniform(0.58, 0.88) + px * bow * rng.uniform(0.2, 0.8),
    y: from.y + dy * rng.uniform(0.58, 0.88) + py * bow * rng.uniform(0.2, 0.8)
  };

  // A fast, long move sometimes shoots past and corrects — very human, and
  // only ever applied when there is room, since the final point must land in
  // the target regardless.
  const doOvershoot =
    dist > 180 && rng.chance(clamp(0.28 * persona.overshoot, 0, 0.5));
  const aim = doOvershoot
    ? {
        x: to.x + (dx / dist) * rng.uniform(6, 26),
        y: to.y + (dy / dist) * rng.uniform(6, 26)
      }
    : to;

  let prev = from;
  for (let i = 1; i <= n; i++) {
    const t = easeInOut(i / n);
    const p = bezier(from, c1, c2, aim, t);
    // Per-point tremor: the hand is not a plotter. Tiny, so it never moves
    // the endpoint out of the target (the last point is snapped below).
    const jx = rng.gauss(0, 0.55 * persona.steadiness);
    const jy = rng.gauss(0, 0.55 * persona.steadiness);
    const pt = { x: Math.round(p.x + jx), y: Math.round(p.y + jy) };
    if (pt.x === prev.x && pt.y === prev.y) continue;
    steps.push({ x: pt.x, y: pt.y, ms: Math.max(1, Math.round((totalMs / n) * rng.uniform(0.6, 1.5))) });
    prev = pt;
  }

  if (doOvershoot) {
    // Settle back onto the real target: a couple of short corrective hops.
    const hops = rng.int(1, 2);
    for (let i = 1; i <= hops; i++) {
      const t = i / hops;
      steps.push({
        x: Math.round(aim.x + (to.x - aim.x) * t),
        y: Math.round(aim.y + (to.y - aim.y) * t),
        ms: Math.round(rng.delay(48, 1.3, 20, 140))
      });
    }
  }

  // Always finish exactly on the intended point — randomisation must never
  // change WHERE the action lands.
  const last = steps[steps.length - 1];
  if (!last || last.x !== to.x || last.y !== to.y) {
    steps.push({ x: to.x, y: to.y, ms: Math.round(rng.delay(28, 1.3, 10, 90)) });
  }
  return steps;
}
