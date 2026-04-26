import { clamp } from '../utils/math.js';

export function Stat({ label, value, bar }) {
  return (
    <div class="card">
      <div class="label">{label}</div>
      <div class="value">{value}</div>
      {bar != null && <div class="bar"><i style={{ width: `${clamp(bar) * 100}%` }} /></div>}
    </div>
  );
}
