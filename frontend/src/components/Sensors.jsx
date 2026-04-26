import { clamp, fmt } from '../utils/math.js';

export function Sensors({ sensors }) {
  return (
    <div>
      {Object.entries(sensors || {}).map(([k, v]) => (
        <div class="sensor" key={k}>
          <span>{k}</span>
          <span class="miniBar"><i style={{ width: `${clamp(v) * 100}%` }} /></span>
          <span>{fmt(v, 2)}</span>
        </div>
      ))}
    </div>
  );
}
