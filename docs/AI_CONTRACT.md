# AI Perception Output & Integration Contract

## 1. Overview
This document specifies the structured perception output schemas, defect classes, taxonomy normalization rules, and integration boundaries for computer vision models operating in the SIH 26124 platform.

Edge perception models stream their outputs to the canonical FastAPI Backend via the thin adapter boundary **`BackendIngestAdapter` (`ai/adapter/backend_adapter.py`)**.

---

## 2. Preserved AI Detectors & Subsystems

All AI detectors and inference models developed on Chirag's branch have been **strictly preserved rather than rewritten**:

| Component | File Path | Detections & Capabilities |
|---|---|---|
| **Road Defect Detector** | `ai/detectors/road_defect_detector.py` | Potholes, surface cracks, damaged pavement, waterlogging / submerged lanes. Estimates civil hazard metrics (`breadth_cm`, `depth_cm`, `dimensions`, `risk_score`, `risk_assessment`). |
| **Infrastructure Detector** | `ai/detectors/infrastructure_detector.py` | Missing road dividers, missing zebra crossings, damaged/missing traffic signs. |
| **Traffic Density Detector** | `ai/detectors/traffic_density_detector.py` | Multi-class vehicle classification (`car`, `bus`, `truck`, `motorcycle`, `auto_rickshaw`), vehicle counting, density index estimation. |
| **Pedestrian Safety Detector**| `ai/detectors/pedestrian_detector.py` | Vulnerable pedestrians and school children crossing in active roadways. |
| **License Plate Recognizer** | `ai/detectors/plate_recognizer.py` | License plate bounding box localization and OCR text recognition with confidence scores. |
| **Vehicle Tracker** | `ai/tracker/vehicle_tracker.py` | SORT/ByteTrack multi-object tracking and rash driving / erratic weaving detection. |
| **GPS Synchronizer** | `ai/telemetry/gps_sync.py` | Frame-to-GPS coordinate and timestamp interpolation. |
| **Edge Optimizer** | `ai/edge_optimizer.py` | 95% bandwidth reduction transmitting structured JSON observations + cropped keyframe evidence. |
| **Hardware Receiver** | `ai/hardware_receiver.py` | UDP listener receiving live ESP32, GPS, and sensor telemetry packets. |

---

## 3. Boundary Adapter & Taxonomy Normalization

The `BackendIngestAdapter` (`ai/adapter/backend_adapter.py`) translates raw edge detection dictionaries into canonical schemas:

```text
Edge Perception Output
         │
         ▼
BackendIngestAdapter
  ├─► Normalizes coordinates: lat/lng keys to latitude/longitude
  ├─► Taxonomy normalization:
  │     event_type="pedestrian" ──► event_type="incident", class_name="vulnerable_pedestrian"
  ├─► Enforces OCR rule: plate_text requires plate_confidence
  └─► Preserves diagnostic metrics in PostgreSQL metadata JSONB:
        risk_score, risk_level, breadth_cm, depth_cm, dimensions, risk_assessment
         │
         ▼
Canonical Backend Endpoints:
  - POST /api/v1/telemetry
  - POST /api/v1/observations
  - POST /api/v1/incidents
```

---

## 4. Structured Perception Observation Schema

Observations dispatched to `POST /api/v1/observations` conform to:

| Field | Type | Required | Description |
|---|---|---|---|
| `event_id` | `string` | Yes | Unique deterministic identifier (e.g., `evt_20260908_101_0042`). |
| `bus_id` | `string` | Yes | Identifier of the sensing fleet vehicle capturing the frame. |
| `timestamp` | `string` (ISO-8601) | Yes | Frame capture timestamp with timezone (e.g., `2026-09-08T15:20:10+05:30`). |
| `latitude` | `number` | Yes | WGS84 latitude of the detection camera/GPS position. |
| `longitude` | `number` | Yes | WGS84 longitude of the detection camera/GPS position. |
| `road_segment_id` | `string` | Optional | Pre-matched road segment ID, or null to trigger PostGIS map matching. |
| `event_type` | `enum` | Yes | Canonical types: `"road_defect"`, `"waterlogging"`, `"traffic"`, `"incident"`. |
| `class_name` | `string` | Optional | Specific class: `"pothole"`, `"major_crack"`, `"water_patch"`, `"illegal_parking"`. |
| `confidence` | `number` ($0.0-1.0$) | Yes | Model prediction confidence score. |
| `severity` | `integer` ($1-4$) | Optional | Severity rating: $1$ (Minor), $2$ (Moderate), $3$ (Severe), $4$ (Critical). |
| `frame_id` | `integer` | Optional | Video stream sequence frame number. |
| `track_id` | `string` | Optional | Persistent tracking ID for dynamic objects. |
| `plate_text` | `string` | Optional | License plate string detected via OCR. |
| `plate_confidence`| `number` ($0.0-1.0$) | Optional | Required if `plate_text` is supplied. |
| `evidence_uri` | `string` (URI) | Optional | HTTPS URL to the stored crop frame or video evidence artifact. |
| `metadata` | `object` (JSONB) | Optional | Preserved AI diagnostics: `risk_score`, `risk_level`, `breadth_cm`, `depth_cm`, `dimensions`, `risk_assessment`. |

---

## 5. Ingestion & Validation Rules

1. **Schema Validation:** Ingestion rejects or flags any observation missing required fields (`event_id`, `bus_id`, `timestamp`, `latitude`, `longitude`, `event_type`, `confidence`).
2. **OCR Plate Rule:** If `plate_text` is supplied, `plate_confidence` is **strictly required**. Omitting `plate_confidence` returns `HTTP 422 Unprocessable Entity`.
3. **Confidence Filtering & Quarantine (< 0.50):**
   - Observations with `confidence < 0.50` are automatically persisted with `status = 'quarantined'`.
   - Returns `HTTP 201 Created` with `{"quarantined": true, "status": "quarantined"}`.
   - Quarantined observations do **not** trigger road score degradation or live dashboard alerts.
4. **Confirmed Observations (>= 0.50):**
   - Snapped to nearest road segment via PostGIS `gis.ST_DWithin` (25m threshold).
   - Recalculates segment health score deterministically with repeat-defect multipliers and confidence weighting.
   - Debounces `segment_history` snapshots to 10-second intervals.
   - Emits `NEW_EVENT` and `SEGMENT_UPDATE` frames over `/ws/live`.
5. **Media Hygiene:** Base64 binary strings are prohibited in JSON payloads. Images must be stored in object storage and passed as `evidence_uri`.
