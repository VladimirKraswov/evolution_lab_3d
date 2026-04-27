import { fmt } from '../utils/math.js';

export function BrainInspector({ data }) {
  if (!data?.body) return null;

  return (
    <div class="brain-inspector">
      <div class="inspector-section">
        <h3>Movement State</h3>
        <div class="stat-row"><span>X/Y/Z:</span> <span>{fmt(data.body.x, 0)} / {fmt(data.body.y, 0)} / {fmt(data.body.z, 0)}</span></div>
        <div class="stat-row"><span>Yaw:</span> <span>{fmt(data.body.yaw, 2)}</span></div>
        <div class="stat-row"><span>Pitch:</span> <span>{fmt(data.body.pitch, 2)}</span></div>
        <div class="stat-row"><span>Last Collision:</span> <span class={data.body.last_collision !== 'none' ? 'col-hit' : ''}>{data.body.last_collision}</span></div>
      </div>

      <div class="inspector-section">
        <h3>Brain Outputs</h3>
        {Object.entries(data.last_cmd || {}).map(([k, v]) => (
          <div class="stat-row" key={k}>
            <span>{k}:</span> <span>{fmt(v, 2)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
