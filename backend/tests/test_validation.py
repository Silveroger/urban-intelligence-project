import pytest
from pydantic import ValidationError
from app.schemas.observations import ObservationCreate
from app.schemas.incidents import IncidentCreate
from app.schemas.telemetry import TelemetryCreate


def test_observation_create_valid():
    obs = ObservationCreate(
        event_id="evt_001",
        bus_id="BUS-101",
        timestamp="2026-09-04T12:00:00Z",
        latitude=30.7333,
        longitude=76.7794,
        event_type="road_defect",
        confidence=0.88,
    )
    assert obs.event_id == "evt_001"
    assert obs.confidence == 0.88


def test_observation_ocr_validation_fail():
    with pytest.raises(ValidationError):
        ObservationCreate(
            event_id="evt_002",
            bus_id="BUS-101",
            timestamp="2026-09-04T12:00:00Z",
            latitude=30.7333,
            longitude=76.7794,
            event_type="incident",
            confidence=0.88,
            plate_text="CH01AB1234",
            # plate_confidence missing!
        )


def test_observation_ocr_validation_success():
    obs = ObservationCreate(
        event_id="evt_003",
        bus_id="BUS-101",
        timestamp="2026-09-04T12:00:00Z",
        latitude=30.7333,
        longitude=76.7794,
        event_type="incident",
        confidence=0.88,
        plate_text="CH01AB1234",
        plate_confidence=0.95,
    )
    assert obs.plate_text == "CH01AB1234"
    assert obs.plate_confidence == 0.95


def test_telemetry_coordinate_validation():
    with pytest.raises(ValueError):
        t = TelemetryCreate(
            bus_id="BUS-101",
            latitude=120.0,  # Invalid latitude
            longitude=76.7794,
        )
        t.validate_geo()
