"""
SIH 26124 — Edge AI & Backend Integration Tests
Tests normalization through BackendIngestAdapter and ingestion through canonical Backend endpoints.
"""

import uuid
import pytest
from httpx import AsyncClient
from ai.adapter.backend_adapter import BackendIngestAdapter
from app.schemas.observations import ObservationCreate
from app.schemas.telemetry import TelemetryCreate
from app.schemas.incidents import IncidentCreate


def test_adapter_observation_normalization():
    """Verify that raw edge perception dictionary is normalized into a valid ObservationCreate payload."""
    adapter = BackendIngestAdapter()
    raw_defect = {
        "event_id": "evt_test_pothole_001",
        "bus_id": "BUS-101",
        "timestamp": "2026-09-07T12:00:00Z",
        "latitude": 30.7350,
        "longitude": 76.7820,
        "event_type": "road_defect",
        "class_name": "pothole",
        "confidence": 0.92,
        "severity": 3,
        "evidence_uri": "/evidence/test_pothole.jpg",
        "risk_score": 78.5,
        "risk_level": "moderate",
        "breadth_cm": 45.0,
        "depth_cm": 6.5,
        "dimensions": {"breadth_cm": 45.0, "depth_cm": 6.5, "area_sq_cm": 292.5},
        "risk_assessment": "Pothole depth poses risk to two-wheelers.",
    }

    payload = adapter.to_observation_payload(raw_defect)
    # Validate against canonical Pydantic model
    obs_obj = ObservationCreate(**payload)
    assert obs_obj.event_id == "evt_test_pothole_001"
    assert obs_obj.event_type == "road_defect"
    assert obs_obj.confidence == 0.92
    assert obs_obj.severity == 3
    assert obs_obj.risk_score == 78.5
    assert obs_obj.depth_cm == 6.5
    assert obs_obj.dimensions["area_sq_cm"] == 292.5
    assert "depth_cm" in obs_obj.metadata


def test_adapter_pedestrian_normalization():
    """Verify that edge event_type='pedestrian' is normalized to canonical event_type='incident'."""
    adapter = BackendIngestAdapter()
    raw_pedestrian = {
        "event_id": "evt_test_ped_002",
        "bus_id": "BUS-101",
        "timestamp": "2026-09-07T12:05:00Z",
        "latitude": 30.7360,
        "longitude": 76.7830,
        "event_type": "pedestrian",
        "class_name": "school_child",
        "confidence": 0.88,
        "severity": 4,
        "risk_score": 90.0,
        "risk_level": "critical",
    }

    payload = adapter.to_observation_payload(raw_pedestrian)
    assert payload["event_type"] == "incident"
    assert payload["class_name"] == "vulnerable_pedestrian"
    obs_obj = ObservationCreate(**payload)
    assert obs_obj.event_type == "incident"
    assert obs_obj.class_name == "vulnerable_pedestrian"


def test_adapter_telemetry_normalization():
    """Verify that hardware UDP telemetry (lat/lng/speed_kmh) normalizes to TelemetryCreate."""
    adapter = BackendIngestAdapter()
    raw_telem = {
        "bus_id": "BUS-101",
        "lat": 30.7333,
        "lng": 76.7794,
        "speed_kmh": 42.5,
        "heading_deg": 180.0,
        "timestamp": "2026-09-07T12:10:00Z",
    }

    payload = adapter.to_telemetry_payload(raw_telem)
    telem_obj = TelemetryCreate(**payload)
    assert telem_obj.bus_id == "BUS-101"
    assert telem_obj.latitude == 30.7333
    assert telem_obj.longitude == 76.7794
    assert telem_obj.speed_kmh == 42.5
    assert telem_obj.heading_deg == 180.0


def test_adapter_incident_normalization():
    """Verify rash driving and plate OCR alerts normalize to IncidentCreate."""
    adapter = BackendIngestAdapter()
    raw_incident = {
        "incident_id": "inc_rash_001",
        "incident_type": "rash_driving",
        "severity": 3,
        "latitude": 30.7370,
        "longitude": 76.7840,
        "timestamp": "2026-09-07T12:15:00Z",
        "vehicle_track_id": "trk_42",
        "plate_text": "CH01AB1234",
        "plate_confidence": 0.95,
        "description": "Erratic lane changes exceeding lateral acceleration threshold",
    }

    payload = adapter.to_incident_payload(raw_incident)
    inc_obj = IncidentCreate(**payload)
    assert inc_obj.incident_type == "rash_driving"
    assert inc_obj.plate_text == "CH01AB1234"
    assert inc_obj.plate_confidence == 0.95


@pytest.mark.asyncio
async def test_end_to_end_telemetry_ingestion(async_client: AsyncClient):
    """Test telemetry ingestion endpoint via normalized adapter payload."""
    adapter = BackendIngestAdapter()
    telem_payload = adapter.to_telemetry_payload({
        "bus_id": "BUS-101",
        "lat": 30.7333,
        "lng": 76.7794,
        "speed_kmh": 35.0,
        "heading_deg": 90.0,
    })

    resp = await async_client.post("/api/v1/telemetry", json=telem_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["bus_id"] == "BUS-101"
    assert data["latitude"] == 30.7333


@pytest.mark.asyncio
async def test_end_to_end_observation_ingestion_with_ai_metadata(async_client: AsyncClient):
    """Test observation ingestion with AI diagnostic risk and dimension metadata."""
    adapter = BackendIngestAdapter()
    unique_id = f"evt_ai_pot_{uuid.uuid4().hex[:8]}"
    obs_payload = adapter.to_observation_payload({
        "event_id": unique_id,
        "bus_id": "BUS-101",
        "timestamp": "2026-09-07T12:20:00Z",
        "latitude": 30.7340,
        "longitude": 76.7800,
        "event_type": "road_defect",
        "class_name": "pothole",
        "confidence": 0.94,
        "severity": 3,
        "risk_score": 82.0,
        "risk_level": "high",
        "breadth_cm": 50.0,
        "depth_cm": 8.0,
        "dimensions": {"breadth_cm": 50.0, "depth_cm": 8.0, "area_sq_cm": 400.0},
        "risk_assessment": "Severe road defect requiring immediate maintenance.",
    })

    resp = await async_client.post("/api/v1/observations", json=obs_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "confirmed"
    assert data["quarantined"] is False


@pytest.mark.asyncio
async def test_video_status_endpoint(async_client: AsyncClient):
    """Test that video pipeline status endpoint returns valid idle state."""
    resp = await async_client.get("/api/v1/ingest/video/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "is_running" in data
    assert "progress" in data
    assert data["is_running"] is False
