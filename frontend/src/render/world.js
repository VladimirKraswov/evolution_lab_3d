import { clamp, fmt } from '../utils/math.js';

function rotatePoint(p, center, camera) {
  const x = p.x - center.x;
  const y = p.y - center.y;
  const z = p.z - center.z;

  const cy = Math.cos(camera.yaw);
  const sy = Math.sin(camera.yaw);
  const cp = Math.cos(camera.pitch);
  const sp = Math.sin(camera.pitch);

  const rx = x * cy - z * sy;
  const rz = x * sy + z * cy;

  const ry = y * cp - rz * sp;
  const rz2 = y * sp + rz * cp;

  return { x: rx, y: ry, z: rz2 };
}

function project(p, center, camera, width, height) {
  const r = rotatePoint(p, center, camera);
  const depth = r.z + camera.distance;
  const scale = 720 / Math.max(80, depth);

  return {
    x: width / 2 + r.x * scale,
    y: height / 2 - r.y * scale,
    s: scale,
    d: depth,
    visible: depth > 30,
  };
}

function line(ctx, a, b, color = '#334155', width = 1) {
  if (!a.visible || !b.visible) return;

  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.beginPath();
  ctx.moveTo(a.x, a.y);
  ctx.lineTo(b.x, b.y);
  ctx.stroke();
}

function drawBackground(ctx, width, height) {
  const g = ctx.createLinearGradient(0, 0, 0, height);
  g.addColorStop(0, '#07111f');
  g.addColorStop(0.5, '#060b16');
  g.addColorStop(1, '#03050b');

  ctx.fillStyle = g;
  ctx.fillRect(0, 0, width, height);

  const glow1 = ctx.createRadialGradient(width * 0.18, height * 0.12, 0, width * 0.18, height * 0.12, width * 0.5);
  glow1.addColorStop(0, 'rgba(59,130,246,.22)');
  glow1.addColorStop(1, 'rgba(59,130,246,0)');
  ctx.fillStyle = glow1;
  ctx.fillRect(0, 0, width, height);

  const glow2 = ctx.createRadialGradient(width * 0.82, height * 0.22, 0, width * 0.82, height * 0.22, width * 0.42);
  glow2.addColorStop(0, 'rgba(34,197,94,.16)');
  glow2.addColorStop(1, 'rgba(34,197,94,0)');
  ctx.fillStyle = glow2;
  ctx.fillRect(0, 0, width, height);
}

function drawGrid(ctx, env, center, camera, width, height) {
  const step = 100;
  const y = 0;

  for (let x = 0; x <= env.width; x += step) {
    const a = project({ x, y, z: 0 }, center, camera, width, height);
    const b = project({ x, y, z: env.depth }, center, camera, width, height);
    line(ctx, a, b, 'rgba(100,116,139,.25)', 1);
  }

  for (let z = 0; z <= env.depth; z += step) {
    const a = project({ x: 0, y, z }, center, camera, width, height);
    const b = project({ x: env.width, y, z }, center, camera, width, height);
    line(ctx, a, b, 'rgba(100,116,139,.25)', 1);
  }
}

function drawBox(ctx, env, center, camera, width, height) {
  const raw = [
    { x: 0, y: 0, z: 0 },
    { x: env.width, y: 0, z: 0 },
    { x: env.width, y: env.height, z: 0 },
    { x: 0, y: env.height, z: 0 },
    { x: 0, y: 0, z: env.depth },
    { x: env.width, y: 0, z: env.depth },
    { x: env.width, y: env.height, z: env.depth },
    { x: 0, y: env.height, z: env.depth },
  ];

  const c = raw.map(p => project(p, center, camera, width, height));
  const edges = [
    [0, 1], [1, 2], [2, 3], [3, 0],
    [4, 5], [5, 6], [6, 7], [7, 4],
    [0, 4], [1, 5], [2, 6], [3, 7],
  ];

  for (const [a, b] of edges) {
    line(ctx, c[a], c[b], 'rgba(148,163,184,.5)', 1.2);
  }
}

function drawFood(ctx, food, center, camera, width, height) {
  const sorted = [...food]
    .map(f => ({ f, q: project(f, center, camera, width, height) }))
    .filter(x => x.q.visible)
    .sort((a, b) => b.q.d - a.q.d);

  for (const { q } of sorted) {
    const r = clamp(q.s * 9, 2.5, 14);

    ctx.beginPath();
    ctx.fillStyle = '#86efac';
    ctx.shadowColor = '#22c55e';
    ctx.shadowBlur = 16;
    ctx.arc(q.x, q.y, r, 0, Math.PI * 2);
    ctx.fill();

    ctx.shadowBlur = 0;
    ctx.strokeStyle = 'rgba(220,252,231,.8)';
    ctx.lineWidth = 1;
    ctx.stroke();
  }
}

function drawBody(ctx, body, center, camera, width, height) {
  const q = project(body, center, camera, width, height);
  if (!q.visible) return;

  const size = clamp(q.s * 28, 10, 38);
  const yawOnScreen = body.yaw - camera.yaw;

  ctx.save();
  ctx.translate(q.x, q.y);
  ctx.rotate(yawOnScreen);

  ctx.shadowColor = '#66e3ff';
  ctx.shadowBlur = 22;

  const grad = ctx.createLinearGradient(0, -size, 0, size);
  grad.addColorStop(0, '#e0f2fe');
  grad.addColorStop(0.45, '#66e3ff');
  grad.addColorStop(1, '#2563eb');

  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.moveTo(0, -size);
  ctx.lineTo(size * 0.72, size * 0.82);
  ctx.lineTo(0, size * 0.35);
  ctx.lineTo(-size * 0.72, size * 0.82);
  ctx.closePath();
  ctx.fill();

  ctx.shadowBlur = 0;
  ctx.strokeStyle = '#dff7ff';
  ctx.lineWidth = 1.2;
  ctx.stroke();

  ctx.strokeStyle = 'rgba(102,227,255,.5)';
  ctx.beginPath();
  ctx.moveTo(0, -size);
  ctx.lineTo(0, -size * 2.2);
  ctx.stroke();

  ctx.restore();
}

export function drawWorld(ctx, data, camera, width, height) {
  ctx.clearRect(0, 0, width, height);
  drawBackground(ctx, width, height);

  const env = data?.environment;
  const body = data?.body;

  if (!env || !body) {
    ctx.fillStyle = '#94a3b8';
    ctx.font = '16px system-ui';
    ctx.fillText('Жду данные WebSocket...', 28, 42);
    return;
  }

  const center = {
    x: env.width / 2,
    y: env.height / 2,
    z: env.depth / 2,
  };

  drawGrid(ctx, env, center, camera, width, height);
  drawBox(ctx, env, center, camera, width, height);
  drawFood(ctx, env.food || [], center, camera, width, height);
  drawBody(ctx, body, center, camera, width, height);

  ctx.fillStyle = 'rgba(15,23,42,.72)';
  ctx.strokeStyle = 'rgba(148,163,184,.25)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.roundRect(16, height - 48, 220, 32, 12);
  ctx.fill();
  ctx.stroke();

  ctx.fillStyle = '#cbd5e1';
  ctx.font = '12px ui-monospace, monospace';
  ctx.fillText(`food ${env.food?.length ?? 0} · zoom ${fmt(camera.distance, 0)}`, 30, height - 28);
}