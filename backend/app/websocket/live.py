import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket.manager import ws_manager

logger = logging.getLogger("urban_intel.websocket.live")

router = APIRouter()


@router.websocket("/live")
async def websocket_live_endpoint(websocket: WebSocket):
    """
    Live streaming WebSocket endpoint at /ws/live.
    Streams real-time frames:
    - BUS_TELEMETRY
    - NEW_EVENT
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Receive text or keep connection alive (e.g. heartbeat ping/pong)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type": "PONG"}')
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket exception: {e}")
        ws_manager.disconnect(websocket)
