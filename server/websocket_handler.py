import asyncio
import logging
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketHandler:
    def __init__(self):
        self.clients = set()

    async def connect(self, websocket: WebSocket, sim_manager=None):
        await websocket.accept()
        self.clients.add(websocket)
        logger.info(f"Client connected, total: {len(self.clients)}")

        # Send init message with static environment data
        init_data = {
            "type": "init",
            "message": "WebSocket успешно подключён к симуляции",
            "config": {
                "env": sim_manager.config.env.__dict__ if sim_manager else {},
                "physics": sim_manager.config.physics.__dict__ if sim_manager else {}
            }
        }
        await websocket.send_json(init_data)

        if sim_manager:
            asyncio.create_task(self._listen(websocket, sim_manager))

    async def _listen(self, websocket: WebSocket, sim_manager):
        try:
            while True:
                data = await websocket.receive_json()
                await sim_manager.command_queue.put(data)
        except WebSocketDisconnect:
            self.disconnect(websocket)
        except Exception as e:
            logger.error(f"WS Listen error: {e}")
            self.disconnect(websocket)

    def disconnect(self, websocket: WebSocket):
        self.clients.discard(websocket)
        logger.info(f"Client disconnected, total: {len(self.clients)}")

    async def broadcast(self, data: dict):
        if not data or not self.clients:
            return

        clients = list(self.clients)
        results = await asyncio.gather(
            *(self._safe_send(ws, data) for ws in clients),
            return_exceptions=True,
        )

        for ws, ok in zip(clients, results):
            if ok is not True:
                self.disconnect(ws)

    async def _safe_send(self, websocket: WebSocket, data: dict):
        try:
            await asyncio.wait_for(websocket.send_json(data), timeout=0.05)
            return True
        except (WebSocketDisconnect, ConnectionResetError, RuntimeError):
            return False
        except asyncio.TimeoutError:
            logger.warning("Slow WebSocket client disconnected")
            return False
        except Exception as e:
            logger.warning(f"Failed to send to client: {e}")
            return False