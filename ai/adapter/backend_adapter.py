"""
SIH 26124 — AI Output Normalization & Backend Ingestion Adapter
Normalizes AI perception outputs from EdgeOptimizer and HardwareReceiver
to strictly adhere to docs/API_CONTRACT.md and docs/AI_CONTRACT.md.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import urllib.request
import urllib.error

logger = logging.getLogger("urban_intel.ai_adapter")


class BackendIngestAdapter:
    """
    Adapter bridging Edge AI perception outputs with the canonical FastAPI Backend REST APIs.
    - Normalizes detector classes and non-canonical event types to canonical taxonomy.
    - Preserves AI hazard diagnostics (risk_score, breadth_cm, depth_cm, dimensions, risk_assessment) in metadata.
    - Dispatches HTTP POST requests to /api/v1/telemetry, /api/v1/observations, and /api/v1/incidents.
    """

    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url.rstrip("/")

    def to_telemetry_payload(self, telemetry_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes bus GPS telemetry dictionary into canonical TelemetryCreate schema dictionary.
        Supports both 'lat'/'lng' and 'latitude'/'longitude'.
        """
        lat = telemetry_payload.get("latitude") if telemetry_payload.get("latitude") is not None else telemetry_payload.get("lat")
        lng = telemetry_payload.get("longitude") if telemetry_payload.get("longitude") is not None else telemetry_payload.get("lng")
        ts = telemetry_payload.get("timestamp") or datetime.now(timezone.utc).isoformat()

        return {
            "bus_id": str(telemetry_payload.get("bus_id", "BUS-101")),
            "latitude": float(lat) if lat is not None else 30.7333,
            "longitude": float(lng) if lng is not None else 76.7794,
            "speed_kmh": float(telemetry_payload["speed_kmh"]) if telemetry_payload.get("speed_kmh") is not None else None,
            "heading_deg": float(telemetry_payload["heading_deg"]) if telemetry_payload.get("heading_deg") is not None else None,
            "accuracy_meters": float(telemetry_payload["accuracy_meters"]) if telemetry_payload.get("accuracy_meters") is not None else None,
            "timestamp": str(ts),
        }

    def to_observation_payload(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes edge AI defect observation dictionary into canonical ObservationCreate schema dictionary.
        Handles event_type enum normalization and packages AI diagnostics into metadata.
        """
        raw_type = str(raw_event.get("event_type", "road_defect")).lower()
        class_name = raw_event.get("class_name")

        # Normalize event_type to canonical Literal["road_defect", "waterlogging", "traffic", "incident"]
        if raw_type == "pedestrian":
            norm_event_type = "incident"
            class_name = "vulnerable_pedestrian"
        elif raw_type == "infrastructure":
            norm_event_type = "road_defect"
        elif raw_type in ("road_defect", "waterlogging", "traffic", "incident"):
            norm_event_type = raw_type
        else:
            norm_event_type = "road_defect"

        lat = raw_event.get("latitude") if raw_event.get("latitude") is not None else raw_event.get("lat", 30.7333)
        lng = raw_event.get("longitude") if raw_event.get("longitude") is not None else raw_event.get("lng", 76.7794)
        ts = raw_event.get("timestamp") or datetime.now(timezone.utc).isoformat()
        evt_id = str(raw_event.get("event_id") or f"evt_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")

        plate_text = raw_event.get("plate_text")
        plate_conf = float(raw_event["plate_confidence"]) if raw_event.get("plate_confidence") is not None else None
        if plate_text and plate_conf is None:
            plate_conf = 0.50

        # AI-specific diagnostics preserved in metadata
        metadata = {
            "risk_score": raw_event.get("risk_score"),
            "risk_level": raw_event.get("risk_level"),
            "breadth_cm": raw_event.get("breadth_cm"),
            "depth_cm": raw_event.get("depth_cm"),
            "dimensions": raw_event.get("dimensions"),
            "risk_assessment": raw_event.get("risk_assessment"),
            "frame_id": raw_event.get("frame_id"),
        }
        if isinstance(raw_event.get("metadata"), dict):
            metadata.update(raw_event["metadata"])

        return {
            "event_id": evt_id,
            "bus_id": str(raw_event.get("bus_id", "BUS-101")),
            "timestamp": str(ts),
            "latitude": float(lat),
            "longitude": float(lng),
            "road_segment_id": raw_event.get("road_segment_id"),
            "event_type": norm_event_type,
            "class_name": class_name,
            "confidence": float(raw_event.get("confidence", 1.0)),
            "severity": int(raw_event.get("severity", 1)),
            "frame_id": raw_event.get("frame_id"),
            "track_id": raw_event.get("track_id"),
            "plate_text": plate_text,
            "plate_confidence": plate_conf,
            "evidence_uri": raw_event.get("evidence_uri"),
            "metadata": metadata,
            # Top-level passthrough for diagnostic fields
            "risk_score": raw_event.get("risk_score"),
            "risk_level": raw_event.get("risk_level"),
            "breadth_cm": raw_event.get("breadth_cm"),
            "depth_cm": raw_event.get("depth_cm"),
            "dimensions": raw_event.get("dimensions"),
            "risk_assessment": raw_event.get("risk_assessment"),
        }

    def to_incident_payload(self, raw_incident: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes tracked offending vehicle incident dictionary into canonical IncidentCreate schema dictionary.
        """
        plate_text = raw_incident.get("plate_text")
        plate_conf = raw_incident.get("plate_confidence")
        if plate_text and plate_conf is None:
            plate_conf = 0.50

        lat = raw_incident.get("latitude") if raw_incident.get("latitude") is not None else raw_incident.get("lat", 30.7350)
        lng = raw_incident.get("longitude") if raw_incident.get("longitude") is not None else raw_incident.get("lng", 76.7820)
        ts = raw_incident.get("timestamp") or datetime.now(timezone.utc).isoformat()

        payload = {
            "incident_type": str(raw_incident.get("incident_type", "rash_driving")),
            "severity": int(raw_incident.get("severity", 1)),
            "latitude": float(lat),
            "longitude": float(lng),
            "timestamp": str(ts),
            "bus_id": str(raw_incident.get("bus_id", "BUS-101")),
            "road_segment_id": raw_incident.get("road_segment_id"),
            "observation_id": raw_incident.get("observation_id"),
            "description": raw_incident.get("description") or f"AI detected {raw_incident.get('incident_type', 'incident')}",
            "vehicle_track_id": raw_incident.get("vehicle_track_id") or raw_incident.get("track_id"),
            "plate_text": plate_text,
            "plate_confidence": float(plate_conf) if plate_conf is not None else None,
            "evidence_uri": raw_incident.get("evidence_uri"),
        }

        if "incident_id" in raw_incident and raw_incident["incident_id"]:
            payload["incident_id"] = str(raw_incident["incident_id"])

        return payload

    def send_telemetry(self, telemetry_payload: Dict[str, Any]) -> bool:
        """Sends bus GPS telemetry to POST /api/v1/telemetry."""
        url = f"{self.backend_url}/api/v1/telemetry"
        canonical_payload = self.to_telemetry_payload(telemetry_payload)
        return self._http_post(url, canonical_payload)

    def send_observation(self, raw_event: Dict[str, Any]) -> bool:
        """Normalizes AI defect observation and sends to POST /api/v1/observations."""
        url = f"{self.backend_url}/api/v1/observations"
        canonical_payload = self.to_observation_payload(raw_event)
        return self._http_post(url, canonical_payload)

    def send_incident(self, raw_incident: Dict[str, Any]) -> bool:
        """Normalizes tracked offending vehicle incident and sends to POST /api/v1/incidents."""
        url = f"{self.backend_url}/api/v1/incidents"
        canonical_payload = self.to_incident_payload(raw_incident)
        return self._http_post(url, canonical_payload)

    def _http_post(self, url: str, data: Dict[str, Any]) -> bool:
        """Dispatches an HTTP POST request with JSON payload."""
        try:
            req_data = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                return resp.status in (200, 201)
        except urllib.error.HTTPError as e:
            logger.warning(f"HTTP Error {e.code} posting to {url}: {e.read().decode('utf-8', errors='ignore')}")
            return False
        except Exception as e:
            logger.warning(f"Connection error posting to {url}: {e}")
            return False
