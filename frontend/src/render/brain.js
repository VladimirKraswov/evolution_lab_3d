import { clamp } from '../utils/math.js';

function drawRoundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
  ctx.fill();
  ctx.stroke();
}

function weightColor(weight, alpha) {
  return weight >= 0
    ? `rgba(102,227,255,${alpha})`
    : `rgba(255,107,107,${alpha})`;
}

export function drawBrain(ctx, brain, width, height) {
  ctx.clearRect(0, 0, width, height);

  ctx.fillStyle = '#020617';
  ctx.fillRect(0, 0, width, height);

  const nodes = brain?.nodes || [];
  const conns = brain?.connections || [];
  const stats = brain?.stats || {};

  ctx.fillStyle = '#94a3b8';
  ctx.font = '11px ui-monospace, monospace';
  ctx.fillText(
    `nodes ${nodes.length} · conns ${stats.enabled_connections ?? conns.length}/${stats.total_connections ?? conns.length}`,
    12,
    16,
  );

  if (!nodes.length) {
    ctx.fillStyle = '#64748b';
    ctx.font = '13px system-ui';
    ctx.fillText('Нет данных мозга', 16, height / 2);
    return;
  }

  const byId = new Map();

  const inputNodes = nodes.filter(n => n.layer === 0);
  const hiddenNodes = nodes.filter(n => n.layer === 1);
  const outputNodes = nodes.filter(n => n.layer === 2);

  const layers = [inputNodes, hiddenNodes, outputNodes];

  layers.forEach((arr, li) => {
    const x =
      layers.length === 1
        ? width / 2
        : 32 + li * ((width - 64) / Math.max(1, layers.length - 1));

    arr.forEach((n, i) => {
      const y = 34 + (i + 1) * ((height - 62) / (arr.length + 1));
      byId.set(n.id, { ...n, x, y });
    });
  });

  const disabled = conns.filter(c => c.enabled === false);
  const enabled = conns.filter(c => c.enabled !== false);

  for (const c of disabled) {
    const a = byId.get(c.from);
    const b = byId.get(c.to);

    if (!a || !b) continue;

    ctx.save();
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = 'rgba(100,116,139,.28)';
    ctx.lineWidth = 1;

    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();

    ctx.restore();
  }

  for (const c of enabled) {
    const a = byId.get(c.from);
    const b = byId.get(c.to);

    if (!a || !b) continue;

    const absW = Math.abs(Number(c.weight) || 0);
    const alpha = clamp(absW / 4, 0.12, 0.9);

    ctx.strokeStyle = weightColor(c.weight, alpha);
    ctx.lineWidth = clamp(absW, 0.5, 3.2);

    ctx.beginPath();
    ctx.moveTo(a.x, a.y);

    const midX = (a.x + b.x) * 0.5;
    const bend = (b.y - a.y) * 0.08;

    ctx.quadraticCurveTo(midX, (a.y + b.y) * 0.5 + bend, b.x, b.y);
    ctx.stroke();
  }

  if (!enabled.length) {
    ctx.fillStyle = 'rgba(15,23,42,.78)';
    ctx.strokeStyle = 'rgba(148,163,184,.25)';
    drawRoundRect(ctx, 12, height - 54, width - 24, 38, 12);

    ctx.fillStyle = '#fbbf24';
    ctx.font = '12px system-ui';
    ctx.fillText('У мозга нет активных связей. Проверь initial_connection и удали старый checkpoint.', 24, height - 30);
  }

  byId.forEach(n => {
    const r = n.type === 'hidden' ? 8 : 7;
    const activation = Number.isFinite(Number(n.activation)) ? Number(n.activation) : 0;
    const act = clamp((activation + 1) / 2, 0, 1);

    ctx.globalAlpha = 1;

    ctx.fillStyle = 'rgba(15,23,42,.9)';
    ctx.strokeStyle = 'rgba(148,163,184,.28)';
    ctx.lineWidth = 1;

    ctx.beginPath();
    ctx.arc(n.x, n.y, r + 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    if (n.type === 'output') {
      ctx.fillStyle = '#fbbf24';
    } else if (n.type === 'input') {
      ctx.fillStyle = '#66e3ff';
    } else {
      ctx.fillStyle = '#c084fc';
    }

    ctx.globalAlpha = 0.35 + act * 0.65;
    ctx.beginPath();
    ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
    ctx.fill();

    ctx.globalAlpha = 1;
    ctx.fillStyle = '#cbd5e1';
    ctx.font = '9px ui-monospace, monospace';
    ctx.fillText(n.label, n.x + 12, n.y + 3);
  });
}