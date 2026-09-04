import json
import logging
from typing import Set, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger("urban_intel.websocket")


class ConnectionManager:
    """Manages active WebSocket connections and thread-safe broadcasts."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Remaining clients: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcasts a JSON dictionary payload to all connected clients."""
        if not self.active_connections:
            return

        payload_str = json.dumps(message)
        dead_connections = set()

        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload_str)
            except Exception as e:
                logger.warning(f"Error sending frame to client: {e}. Marking for removal.")
                dead_connections.add(connection)

        for dead in dead_connections:
            self.disconnect(dead)


ws_manager = ConnectionManager()
