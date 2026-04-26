export const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, Number(v) || 0));

export const fmt = (v, n = 1) =>
  Number.isFinite(Number(v)) ? Number(v).toFixed(n) : '—';

export const lerp = (a, b, t) => a + (b - a) * t;

export function lerpAngle(a, b, t) {
  let d = ((b - a + Math.PI) % (Math.PI * 2)) - Math.PI;
  return a + d * t;
}

export function smoothstep(t) {
  t = clamp(t);
  return t * t * (3 - 2 * t);
}