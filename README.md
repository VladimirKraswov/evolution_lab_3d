# Evolution Lab 3D — Preact + Vite

## Production-like run

```bash
./run.sh
```

Открой: http://localhost:3030

## Dev mode

```bash
./dev.sh
```

Открой: http://localhost:5173

Vite проксирует `/ws` на FastAPI backend `localhost:3030`.

## Frontend structure

```text
frontend/
  index.html
  package.json
  vite.config.js
  src/
    main.jsx
    App.jsx
    components/
      BrainCanvas.jsx
      Hud.jsx
      Sensors.jsx
      Stat.jsx
      Toolbar.jsx
      WorldCanvas.jsx
    hooks/
      useSocket.js
    render/
      brain.js
      world.js
    styles/
      global.css
    utils/
      math.js
```
