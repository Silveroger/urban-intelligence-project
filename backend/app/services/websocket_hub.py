"""
SIH 26124 — WebSocket Broadcasting Hub
Manages active dashboard client connections and broadcasts live deltas.
Conforms to docs/API_CONTRACT.md (§3).
"""

import json
from typing import Any, Dict, List
from fastapi import WebSocket


class WebSocketHub:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_json(self, message: Dict[str, Any]):
        """
        Broadcasts a JSON frame to all connected clients.
        Frame shape: {"type": "NEW_EVENT" | "BUS_TELEMETRY" | "NEW_INCIDENT", "payload": ...}
        """
        stale = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                stale.append(connection)

        for s in stale:
            self.disconnect(s)


ws_hub = WebSocketHub()
