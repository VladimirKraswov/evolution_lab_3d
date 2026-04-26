import { useEffect, useRef } from 'preact/hooks';
import { drawBrain } from '../render/brain.js';

export function BrainCanvas({ brain }) {
  const ref = useRef(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.floor(rect.width * dpr));
    canvas.height = Math.max(1, Math.floor(rect.height * dpr));
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    drawBrain(ctx, brain, rect.width, rect.height);
  }, [brain]);

  const stats = brain?.connections ? {
    total: brain.connections.length,
    enabled: brain.connections.filter(c => c.enabled).length,
    nodes: brain.nodes?.length || 0
  } : null;

  return (
    <div class="brainContainer">
      <canvas class="brain" ref={ref} />
      {stats && (
        <div class="brainStats">
          {stats.nodes} nodes · {stats.enabled}/{stats.total} conns
        </div>
      )}
    </div>
  );
}
