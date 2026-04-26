import { clamp, fmt } from '../utils/math.js';

const textureCache = new Map();

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

function polygon(ctx, points, fillStyle, strokeStyle = null, lineWidth = 1) {
  if (points.some(p => !p.visible)) return;

  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);

  for (let i = 1; i < points.length; i++) {
    ctx.lineTo(points[i].x, points[i].y);
  }

  ctx.closePath();

  if (fillStyle) {
    ctx.fillStyle = fillStyle;
    ctx.fill();
  }

  if (strokeStyle) {
    ctx.strokeStyle = strokeStyle;
    ctx.lineWidth = lineWidth;
    ctx.stroke();
  }
}

function getTexturePattern(ctx, url) {
  const src = url || '/data/textures/sand.png';
  let rec = textureCache.get(src);

  if (!rec) {
    const img = new Image();

    rec = {
      img,
      ready: false,
      pattern: null,
    };

    img.onload = () => {
      rec.ready = true;
      rec.pattern = null;
    };

    img.src = src;
    textureCache.set(src, rec);
  }

  if (!rec.ready || !rec.img.complete) return null;

  if (!rec.pattern) {
    rec.pattern = ctx.createPattern(rec.img, 'repeat');
  }

  return rec.pattern;
}

function drawBackground(ctx, width, height) {
  const g = ctx.createLinearGradient(0, 0, 0, height);
  g.addColorStop(0, '#07111f');
  g.addColorStop(0.5, '#061525');
  g.addColorStop(1, '#020713');

  ctx.fillStyle = g;
  ctx.fillRect(0, 0, width, height);

  const glow1 = ctx.createRadialGradient(
    width * 0.18,
    height * 0.12,
    0,
    width * 0.18,
    height * 0.12,
    width * 0.5,
  );

  glow1.addColorStop(0, 'rgba(59,130,246,.22)');
  glow1.addColorStop(1, 'rgba(59,130,246,0)');

  ctx.fillStyle = glow1;
  ctx.fillRect(0, 0, width, height);

  const glow2 = ctx.createRadialGradient(
    width * 0.82,
    height * 0.22,
    0,
    width * 0.82,
    height * 0.22,
    width * 0.42,
  );

  glow2.addColorStop(0, 'rgba(34,197,94,.14)');
  glow2.addColorStop(1, 'rgba(34,197,94,0)');

  ctx.fillStyle = glow2;
  ctx.fillRect(0, 0, width, height);

  for (let i = 0; i < 18; i++) {
    const x = ((i * 97) % Math.max(1, width));
    const y = ((i * 53) % Math.max(1, height));
    const r = 1.5 + (i % 5) * 0.7;

    ctx.fillStyle = `rgba(186,230,253,${0.05 + (i % 4) * 0.025})`;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
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
    line(ctx, c[a], c[b], 'rgba(226,246,255,.48)', 1.25);
  }
}

function drawAquariumBackGlass(ctx, env, center, camera, width, height) {
  const faces = [
    [
      { x: 0, y: 0, z: env.depth },
      { x: env.width, y: 0, z: env.depth },
      { x: env.width, y: env.height, z: env.depth },
      { x: 0, y: env.height, z: env.depth },
    ],
    [
      { x: 0, y: 0, z: 0 },
      { x: 0, y: 0, z: env.depth },
      { x: 0, y: env.height, z: env.depth },
      { x: 0, y: env.height, z: 0 },
    ],
    [
      { x: env.width, y: 0, z: 0 },
      { x: env.width, y: 0, z: env.depth },
      { x: env.width, y: env.height, z: env.depth },
      { x: env.width, y: env.height, z: 0 },
    ],
    [
      { x: 0, y: env.height, z: 0 },
      { x: env.width, y: env.height, z: 0 },
      { x: env.width, y: env.height, z: env.depth },
      { x: 0, y: env.height, z: env.depth },
    ],
  ];

  for (const face of faces) {
    const pts = face.map(p => project(p, center, camera, width, height));
    polygon(ctx, pts, 'rgba(56,189,248,.055)', 'rgba(125,211,252,.16)', 1);
  }
}

function drawAquariumFrontGlass(ctx, env, center, camera, width, height) {
  const face = [
    { x: 0, y: 0, z: 0 },
    { x: env.width, y: 0, z: 0 },
    { x: env.width, y: env.height, z: 0 },
    { x: 0, y: env.height, z: 0 },
  ];

  const pts = face.map(p => project(p, center, camera, width, height));

  polygon(ctx, pts, 'rgba(125,211,252,.035)', 'rgba(226,246,255,.2)', 1);
}

function drawSandMesh(ctx, terrain, center, camera, width, height) {
  if (!terrain?.vertices?.length || !terrain?.cells?.length) return;

  const pattern = getTexturePattern(ctx, terrain.texture);

  const projected = terrain.vertices.map(v => ({
    source: v,
    q: project(v, center, camera, width, height),
  }));

  const cells = terrain.cells
    .map(cell => {
      const a = projected[cell.a];
      const b = projected[cell.b];
      const c = projected[cell.c];
      const d = projected[cell.d];

      return {
        points: [a.q, b.q, c.q, d.q],
        depth: (a.q.d + b.q.d + c.q.d + d.q.d) / 4,
        height: (a.source.y + b.source.y + c.source.y + d.source.y) / 4,
        slope: Math.abs(a.source.y - c.source.y) + Math.abs(b.source.y - d.source.y),
      };
    })
    .filter(cell => cell.points.some(p => p.visible))
    .sort((a, b) => b.depth - a.depth);

  for (const cell of cells) {
    const shade = clamp(cell.height / 95, 0.08, 0.34);
    const slopeShade = clamp(cell.slope / 90, 0.02, 0.16);

    polygon(
      ctx,
      cell.points,
      pattern || '#caa96f',
      'rgba(83,58,28,.2)',
      0.65,
    );

    polygon(
      ctx,
      cell.points,
      `rgba(255,244,196,${shade * 0.24})`,
      null,
    );

    polygon(
      ctx,
      cell.points,
      `rgba(48,30,12,${slopeShade})`,
      null,
    );
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

function strokeBlade(ctx, points, baseWidth, colorTop, colorBottom, glow = 0) {
  if (points.length < 2 || points.some(p => !p.visible)) return;

  const top = points[points.length - 1];
  const base = points[0];

  const grad = ctx.createLinearGradient(base.x, base.y, top.x, top.y);
  grad.addColorStop(0, colorBottom);
  grad.addColorStop(1, colorTop);

  ctx.strokeStyle = grad;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.lineWidth = baseWidth;
  ctx.shadowColor = glow > 0 ? 'rgba(34,197,94,.35)' : 'transparent';
  ctx.shadowBlur = glow;

  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);

  if (points.length === 2) {
    ctx.lineTo(points[1].x, points[1].y);
  } else {
    for (let i = 1; i < points.length - 1; i++) {
      const midX = (points[i].x + points[i + 1].x) * 0.5;
      const midY = (points[i].y + points[i + 1].y) * 0.5;
      ctx.quadraticCurveTo(points[i].x, points[i].y, midX, midY);
    }

    const last = points[points.length - 1];
    ctx.lineTo(last.x, last.y);
  }

  ctx.stroke();
  ctx.shadowBlur = 0;
}

function drawAlgae(ctx, algae, body, center, camera, width, height, timeSeconds) {
  if (!Array.isArray(algae) || algae.length === 0) return;

  const sorted = algae
    .map(item => {
      const anchor = project(item, center, camera, width, height);
      return { item, anchor };
    })
    .filter(entry => entry.anchor.visible)
    .sort((a, b) => b.anchor.d - a.anchor.d);

  for (const { item } of sorted) {
    const bladeCount = 3;
    const segments = item.segments || 6;

    const dxBody = body ? body.x - item.x : 9999;
    const dyBody = body ? body.y - item.y : 9999;
    const dzBody = body ? body.z - item.z : 9999;
    const planarDist = Math.sqrt(dxBody * dxBody + dzBody * dzBody);
    const fullDist = Math.sqrt(dxBody * dxBody + dyBody * dyBody + dzBody * dzBody);

    const proximity = clamp(1 - fullDist / 135, 0, 1);
    const pressure = proximity * proximity;

    const awayX = planarDist > 0.0001 ? -dxBody / planarDist : 0;
    const awayZ = planarDist > 0.0001 ? -dzBody / planarDist : 0;

    for (let bladeIndex = 0; bladeIndex < bladeCount; bladeIndex++) {
      const bladePhase = item.phase + bladeIndex * 0.9;
      const side = bladeIndex - 1;

      const baseX = item.x + side * item.spread * 0.38;
      const baseZ = item.z + Math.sin(bladePhase) * item.spread * 0.18;
      const baseY = item.y + 1.0;

      const points = [];

      for (let i = 0; i <= segments; i++) {
        const t = i / segments;
        const bendK = Math.pow(t, 1.45);

        const ambientWave =
          Math.sin(timeSeconds * (1.2 + item.stiffness * 0.6) + bladePhase + t * 2.1) *
            (4.0 + 7.0 * t) +
          Math.cos(timeSeconds * 0.75 + bladePhase * 0.7 + t * 1.6) * (1.5 + 1.8 * t);

        const swimPush = pressure * 26 * bendK;
        const leanOffset = item.lean * item.height * bendK;
        const sideSpread = side * item.spread * 0.25 * bendK;

        const worldX =
          baseX +
          (ambientWave + leanOffset + sideSpread) * 0.72 * bendK +
          awayX * swimPush;

        const worldY = baseY + item.height * t;
        const worldZ =
          baseZ +
          Math.cos(timeSeconds * 0.95 + bladePhase + t * 2.3) * 1.8 * bendK +
          awayZ * swimPush * 0.85;

        points.push(project(
          { x: worldX, y: worldY, z: worldZ },
          center,
          camera,
          width,
          height,
        ));
      }

      const baseWidth = clamp((item.width + (2 - bladeIndex) * 0.4) * points[0].s * 0.95, 1.2, 7.5);

      const greenBase = 110 + Math.round(item.color_shift * 35);
      const greenTop = 170 + Math.round(item.color_shift * 25);
      const blueShift = 70 + Math.round(item.color_shift * 18);

      const colorBottom = `rgba(${30 + bladeIndex * 3},${greenBase},${42 + bladeIndex * 2},0.95)`;
      const colorTop = `rgba(${80 + bladeIndex * 8},${greenTop},${blueShift},0.9)`;

      strokeBlade(
        ctx,
        points,
        baseWidth,
        colorTop,
        colorBottom,
        pressure > 0.08 ? 6 + pressure * 8 : 0,
      );
    }
  }
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

  const timeSeconds =
    typeof data?.timestamp === 'number'
      ? data.timestamp
      : performance.now() / 1000;

  drawAquariumBackGlass(ctx, env, center, camera, width, height);
  drawSandMesh(ctx, env.terrain, center, camera, width, height);
  drawAlgae(ctx, env.algae || [], body, center, camera, width, height, timeSeconds);
  drawBox(ctx, env, center, camera, width, height);

  drawFood(ctx, env.food || [], center, camera, width, height);
  drawBody(ctx, body, center, camera, width, height);

  drawAquariumFrontGlass(ctx, env, center, camera, width, height);

  ctx.fillStyle = 'rgba(15,23,42,.72)';
  ctx.strokeStyle = 'rgba(148,163,184,.25)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.roundRect(16, height - 48, 360, 32, 12);
  ctx.fill();
  ctx.stroke();

  ctx.fillStyle = '#cbd5e1';
  ctx.font = '12px ui-monospace, monospace';
  ctx.fillText(
    `food ${env.food?.length ?? 0} · algae ${env.algae?.length ?? 0} · zoom ${fmt(camera.distance, 0)} · aquarium`,
    30,
    height - 28,
  );
}