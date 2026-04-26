import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .simulation_manager import SimulationManager
from .websocket_handler import WebSocketHandler
from evolution.runner import NEATRunner

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST = ROOT / "frontend" / "dist"


def create_app(sim_manager: SimulationManager, neat_runner: NEATRunner) -> FastAPI:
    ws_handler = WebSocketHandler()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        sim_task = asyncio.create_task(sim_manager.run_loop(ws_handler))
        logger.info("Симуляция запущена")
        yield
        sim_task.cancel()
        try:
            await sim_task
        except asyncio.CancelledError:
            logger.info("Симуляция остановлена")

    app = FastAPI(lifespan=lifespan)

    if FRONTEND_DIST.exists():
        assets = FRONTEND_DIST / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await ws_handler.connect(websocket, sim_manager=sim_manager)

        if sim_manager.visualization_data:
            try:
                await websocket.send_json(sim_manager.visualization_data)
            except Exception as e:
                logger.warning(f"Не удалось отправить initial snapshot: {e}")

        try:
            # We don't need the manual receive loop here because ws_handler.connect
            # now spawns a listener task that pipes to sim_manager.command_queue
            while True:
                await asyncio.sleep(10)
        except WebSocketDisconnect:
            logger.info("Клиент отключился")
        except Exception as e:
            logger.warning(f"Ошибка WebSocket: {e}")
        finally:
            ws_handler.disconnect(websocket)

    @app.get("/api/state")
    async def api_state():
        return sim_manager.visualization_data or {"status": "warming_up"}

    @app.get("/api/health")
    async def api_health():
        return {
            "ok": True,
            "gen": neat_runner.generation,
            "clients": len(ws_handler.clients),
            "sim_hz": sim_manager.sim_hz,
            "broadcast_hz": sim_manager.broadcast_hz,
            "demo_active": sim_manager.demo_active,
        }

    @app.get("/")
    async def root():
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(index)

        return HTMLResponse(
            "<h1>Frontend не собран</h1>"
            "<p>Запусти: <code>cd frontend && npm install && npm run build</code></p>",
            status_code=503,
        )

    return app