import { clamp } from '../utils/math.js';

export function drawBrain(ctx, brain, width, height) {
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = '#020617';
  ctx.fillRect(0, 0, width, height);

  const nodes = brain?.nodes || [];
  const conns = brain?.connections || [];
  const byId = new Map();
  const layers = [
    nodes.filter(n => n.layer === 0),
    nodes.filter(n => n.layer === 1),
    nodes.filter(n => n.layer === 2),
  ];

  layers.forEach((arr, li) => arr.forEach((n, i) => {
    const x = 34 + li * ((width - 68) / 2);
    const y = 24 + (i + 1) * ((height - 48) / (arr.length + 1));
    byId.set(n.id, { ...n, x, y });
  }));

  conns.forEach(c => {
    const a = byId.get(c.from), b = byId.get(c.to);
    if (!a || !b) return;

    if (!c.enabled) {
      ctx.setLineDash([2, 2]);
      ctx.strokeStyle = 'rgba(100, 116, 139, 0.2)';
      ctx.lineWidth = 0.5;
    } else {
      ctx.setLineDash([]);
      const alpha = clamp(Math.abs(c.weight) / 4, .15, .9);
      ctx.strokeStyle = c.weight >= 0 ? `rgba(102, 227, 255, ${alpha})` : `rgba(255, 107, 107, ${alpha})`;
      ctx.lineWidth = clamp(Math.abs(c.weight), 0.5, 4);
    }

    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  });
  ctx.setLineDash([]);

  byId.forEach(n => {
    const r = n.type === 'hidden' ? 8 : 7;
    const act = clamp((Number(n.activation) + 1) / 2);
    ctx.fillStyle = n.type === 'output' ? '#fbbf24' : n.type === 'input' ? '#66e3ff' : '#c084fc';
    ctx.globalAlpha = .35 + act * .65;
    ctx.beginPath();
    ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.fillStyle = '#94a3b8';
    ctx.font = '10px ui-monospace, monospace';
    ctx.fillText(n.label, n.x + 11, n.y + 3);
  });
}
