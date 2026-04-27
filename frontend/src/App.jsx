import { useState } from 'preact/hooks';
import { useSocket } from './hooks/useSocket.js';
import { fmt } from './utils/math.js';
import { WorldCanvas } from './components/WorldCanvas.jsx';
import { BrainCanvas } from './components/BrainCanvas.jsx';
import { Stat } from './components/Stat.jsx';
import { Sensors } from './components/Sensors.jsx';
import { BrainInspector } from './components/BrainInspector.jsx';
import { Hud } from './components/Hud.jsx';
import { Toolbar } from './components/Toolbar.jsx';

const DEFAULT_CAMERA = {
  yaw: 0,
  pitch: -0.32,
  distance: 980,
};

export function App() {
  const { connected, data, log, send } = useSocket();
  const [camera, setCamera] = useState(DEFAULT_CAMERA);
  const energy = data?.body ? data.body.energy / data.body.max_energy : 0;

  const resetCamera = () => setCamera(DEFAULT_CAMERA);

  return (
    <div class="app">
      <main class="stage">
        <Hud connected={connected} data={data} />
        <Toolbar send={send} camera={camera} setCamera={setCamera} resetCamera={resetCamera} />
        <WorldCanvas data={data} camera={camera} setCamera={setCamera} />
        <div class="sceneHint">Drag — rotate · Wheel — zoom · Double click — reset</div>
      </main>

      <aside class="side">
        <h1>Evolution Lab 3D</h1>

        <div class="grid">
          <Stat label="Energy" value={fmt(data?.body?.energy, 1)} bar={energy} />
          <Stat label="Food" value={data?.environment?.food?.length ?? '—'} />
          <Stat label="FPS" value={data?.fps ?? '—'} />
          <Stat label="Demo steps" value={data?.demo_steps ?? '—'} bar={(data?.demo_steps || 0) / 1500} />
        </div>

        <h2>Brain graph</h2>
        <BrainCanvas brain={data?.brain} />

        <h2>Brain Inspector</h2>
        <BrainInspector data={data} />

        <h2>Sensors</h2>
        <Sensors sensors={data?.sensors} />

        <h2>WebSocket</h2>
        <div class="card log">{log}</div>
      </aside>
    </div>
  );
}