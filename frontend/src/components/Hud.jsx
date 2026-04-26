import { fmt } from '../utils/math.js';

export function Hud({ connected, data }) {
  return (
    <div class="hud">
      <span class="pill"><i class={`status ${connected ? 'ok' : ''}`} />{connected ? 'WS online' : 'WS offline'}</span>
      <span class="pill">gen {data?.gen ?? '—'}</span>
      <span class="pill">fitness {fmt(data?.best_fitness, 1)}</span>
      {data?.training?.busy && <span class="pill busy">training...</span>}
      <span class="pill">entropy {data?.entropy?.source ?? '—'} / {data?.entropy?.pool ?? 0}</span>
    </div>
  );
}
