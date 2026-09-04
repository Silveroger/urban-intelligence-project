import pytest
from unittest.mock import AsyncMock
from app.websocket.manager import ConnectionManager


@pytest.mark.asyncio
async def test_websocket_manager_connect_and_broadcast():
    manager = ConnectionManager()
    mock_ws = AsyncMock()

    await manager.connect(mock_ws)
    assert len(manager.active_connections) == 1
    mock_ws.accept.assert_called_once()

    await manager.broadcast({"type": "TEST_FRAME", "payload": {"key": "val"}})
    mock_ws.send_text.assert_called_once()

    manager.disconnect(mock_ws)
    assert len(manager.active_connections) == 0


@pytest.mark.asyncio
async def test_websocket_manager_dead_connection_cleanup():
    manager = ConnectionManager()
    failing_ws = AsyncMock()
    failing_ws.send_text.side_effect = Exception("Connection lost")

    await manager.connect(failing_ws)
    assert len(manager.active_connections) == 1

    # Broadcast should catch the error and remove the dead connection
    await manager.broadcast({"test": 123})
    assert len(manager.active_connections) == 0
