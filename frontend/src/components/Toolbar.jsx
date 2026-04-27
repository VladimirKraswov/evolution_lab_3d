import { clamp } from '../utils/math.js';

export function Toolbar({ send, camera, setCamera, resetCamera }) {
  const zoom = (delta) => {
    setCamera(prev => ({
      ...prev,
      distance: clamp(prev.distance + delta, 380, 2200),
    }));
  };

  return (
    <div class="toolbar">
      <button onClick={() => send({ action: 'next_gen' })}>Next gen</button>
      <button onClick={() => send({ action: 'skip_gens', count: 5 })}>+5 gens</button>
      <button onClick={() => send({ action: 'skip_gens', count: 20 })}>+20 gens</button>
      <button onClick={() => send({ action: 'reset_demo' })}>Reset sim</button>
      <button onClick={() => send({ action: 'reset_training' })}>Reset training</button>

      <span class="toolbarDivider" />

      <button onClick={() => zoom(-120)}>Zoom +</button>
      <button onClick={() => zoom(120)}>Zoom −</button>
      <button onClick={resetCamera}>Reset view</button>
    </div>
  );
}