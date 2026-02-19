from typing import List
from fastapi import WebSocket
import asyncio


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self.lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        """Send a text message to all connected clients."""
        async with self.lock:
            conns = list(self.active_connections)
        for conn in conns:
            try:
                await conn.send_text(message)
            except Exception:
                # best-effort: ignore failures and remove dead connections later
                pass


manager = WebSocketManager()
