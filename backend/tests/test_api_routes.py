from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient
from app.main import app
from app.db.database import get_db
from app.models.bus import Bus
from app.models.observation import Observation
from app.models.incident import Incident


@pytest.fixture
def mock_db_session():
    mock_session = AsyncMock()

    # Default execute mock
    async def mock_execute(stmt, *args, **kwargs):
        mock_result = MagicMock()
        stmt_str = str(stmt)

        if "road_segments" in stmt_str:
            sample_row = (
                "de79e250-5dea-4ecd-85bb-25f972d9d91c",
                "TEST ROAD - SECTOR 1",
                '{"type": "LineString", "coordinates": [[76.7794, 30.7333], [76.7820, 30.7350]]}',
                85.5,
                0.92,
                0,
                0,
                14,
                datetime.now(timezone.utc),
            )
            mock_result.fetchall.return_value = [sample_row]
            mock_result.all.return_value = [(85.5,)]
            mock_result.scalar_one_or_none.return_value = None
            return mock_result

        elif "buses" in stmt_str:
            mock_bus = Bus(
                bus_id="420c49b0-8442-4175-b5b8-424bf2d7fcc8",
                vehicle_number="TEST-BUS-001",
                status="active",
                last_latitude=30.7333,
                last_longitude=76.7794,
                last_ping=datetime.now(timezone.utc),
            )
            mock_result.scalars.return_value.all.return_value = [mock_bus]
            mock_result.all.return_value = [(mock_bus, 90.0)]
            return mock_result

        elif "observations" in stmt_str:
            mock_obs = Observation(
                observation_id="evt_pot_001",
                bus_id="420c49b0-8442-4175-b5b8-424bf2d7fcc8",
                segment_id="de79e250-5dea-4ecd-85bb-25f972d9d91c",
                event_type="road_defect",
                severity=3,
                confidence=0.89,
                observed_at=datetime.now(timezone.utc),
                metadata_json={
                    "event_id": "evt_pot_001",
                    "class_name": "pothole_deep",
                    "latitude": 30.7333,
                    "longitude": 76.7794,
                },
                status="confirmed",
            )
            mock_result.scalars.return_value.all.return_value = [mock_obs]
            return mock_result

        elif "incidents" in stmt_str:
            mock_inc = Incident(
                incident_id="inc_001",
                segment_id="de79e250-5dea-4ecd-85bb-25f972d9d91c",
                incident_type="illegal_parking",
                severity=2,
                status="open",
                recorded_at=datetime.now(timezone.utc),
            )
            mock_result.scalars.return_value.all.return_value = [mock_inc]
            mock_result.scalar.return_value = 1
            return mock_result

        mock_result.fetchall.return_value = []
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalar.return_value = 1
        mock_result.all.return_value = [(85.5,)]
        return mock_result

    mock_session.execute.side_effect = mock_execute
    return mock_session


@pytest.mark.asyncio
async def test_get_segments_geojson_format(async_client: AsyncClient, mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    try:
        response = await async_client.get("/api/v1/segments/geojson")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 1
        feature = data["features"][0]
        assert feature["id"] == "de79e250-5dea-4ecd-85bb-25f972d9d91c"
        assert feature["properties"]["name"] == "TEST ROAD - SECTOR 1"
        assert feature["properties"]["condition_score"] == 85.5
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_get_segments_flat_format(async_client: AsyncClient, mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    try:
        response = await async_client.get("/api/v1/segments/geojson?format=flat")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["segment_id"] == "de79e250-5dea-4ecd-85bb-25f972d9d91c"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_get_events(async_client: AsyncClient, mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    try:
        response = await async_client.get("/api/v1/events")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["event_id"] == "evt_pot_001"
        # Contract Verification: severity MUST remain numeric 1-4
        assert data[0]["severity"] == 3
        assert isinstance(data[0]["severity"], int)
        assert data[0]["severity_label"] == "high"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_get_incidents(async_client: AsyncClient, mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    try:
        response = await async_client.get("/api/v1/incidents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["incident_type"] == "illegal_parking"
        # Contract Verification: severity MUST remain numeric 1-4
        assert data[0]["severity"] == 2
        assert isinstance(data[0]["severity"], int)
        assert data[0]["severity_label"] == "moderate"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_get_buses(async_client: AsyncClient, mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    try:
        response = await async_client.get("/api/v1/buses")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["bus_id"] == "420c49b0-8442-4175-b5b8-424bf2d7fcc8"
        assert data[0]["vehicle_number"] == "TEST-BUS-001"
        assert data[0]["heading_deg"] == 90.0
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_post_observation_ocr_missing_confidence(async_client: AsyncClient):
    payload = {
        "event_id": "evt_test_001",
        "bus_id": "TEST-BUS-001",
        "timestamp": "2026-09-04T12:00:00Z",
        "latitude": 30.7333,
        "longitude": 76.7794,
        "event_type": "incident",
        "confidence": 0.90,
        "plate_text": "CH01AB1234",
    }
    response = await async_client.post("/api/v1/observations", json=payload)
    assert response.status_code == 422
    error_data = response.json()
    assert "error" in error_data
    assert error_data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_get_analytics_summary(async_client: AsyncClient, mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    try:
        response = await async_client.get("/api/v1/analytics/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_segments" in data
        assert "average_condition_score" in data
        assert "active_buses_count" in data
        assert "condition_distribution" in data
        assert data["total_segments"] >= 1
    finally:
        app.dependency_overrides.pop(get_db, None)

