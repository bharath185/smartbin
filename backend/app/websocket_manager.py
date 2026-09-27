import json
import logging
from typing import List
from fastapi import WebSocket

logger = logging.getLogger("smartbin.ws")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total active: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast JSON message to all active WebSocket clients."""
        logger.info(f"Broadcasting WS message: {message.get('type')}")
        payload_str = json.dumps(message)
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload_str)
            except Exception as e:
                logger.warning(f"Error sending to WS client: {e}")
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)

# Global singleton
ws_manager = ConnectionManager()
