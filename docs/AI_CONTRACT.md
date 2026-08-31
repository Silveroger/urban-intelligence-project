# AI Perception Output Contract

## 1. Overview
This document specifies the structured JSON schema that edge and cloud perception models must produce. The backend ingestion service validates all inference outputs against these contracts before spatial aggregation and persistence.

---

## 2. Structured Perception Observation Schema

Each perception event produced by computer vision models must conform to the following schema:

| Field | Type | Required | Description |
|---|---|---|---|
| `event_id` | `string` | Yes | Unique deterministic identifier (e.g., `evt_20260831_101_0042`). |
| `bus_id` | `string` | Yes | Identifier of the sensing fleet vehicle capturing the frame. |
| `timestamp` | `string` (ISO-8601) | Yes | Frame capture timestamp with timezone (e.g., `2026-08-31T15:20:10+05:30`). |
| `latitude` | `number` | Yes | WGS84 latitude of the detection camera/GPS position. |
| `longitude` | `number` | Yes | WGS84 longitude of the detection camera/GPS position. |
| `road_segment_id` | `string` | Optional | Matched road segment ID if edge map-matching was executed. |
| `event_type` | `enum` | Yes | One of: `"road_defect"`, `"waterlogging"`, `"traffic"`, `"incident"`. |
| `class_name` | `string` | Optional | Specific perception class: `"pothole"`, `"alligator_crack"`, `"rutting"`, `"water_patch"`, `"illegal_parking"`, `"congestion_cluster"`. |
| `confidence` | `number` ($0.0-1.0$) | Yes | Model prediction confidence score. |
| `severity` | `integer` ($1-4$) | Optional | Severity rating: $1$ (Minor), $2$ (Moderate), $3$ (Severe), $4$ (Critical). |
| `frame_id` | `integer` | Optional | Video stream sequence frame number. |
| `track_id` | `string` | Optional | Persistent tracking ID for dynamic objects (e.g., vehicles). |
| `plate_text` | `string` | Optional | License plate string detected via OCR. |
| `plate_confidence`| `number` ($0.0-1.0$) | Optional | OCR confidence score for the detected plate text. |
| `evidence_uri` | `string` (URI) | Optional | HTTPS URL to the stored crop frame or video evidence artifact. |

---

## 3. Class-Specific Contract Guidelines

### 3.1 Road Defect Events (`road_defect`)
- `class_name`: `"pothole"`, `"major_crack"`, `"surface_wear"`.
- `severity`: Assigned based on bounding box dimension, depth estimation, or surface area ratio.
- `evidence_uri`: Must link to a cropped, bounded keyframe image highlighting the defect.

### 3.2 Waterlogging Events (`waterlogging`)
- `class_name`: `"water_patch"`, `"submerged_lane"`.
- `severity`: Reflects estimated water depth and lane obstruction impact ($1-4$).

### 3.3 Traffic & Incident Events (`traffic`, `incident`)
- `class_name`: `"illegal_parking"`, `"lane_blockage"`, `"bus_lane_encroachment"`.
- `plate_text` & `plate_confidence`: Must only be populated when optical character recognition is performed. OCR output must never be inferred without an associated `plate_confidence`.

---

## 4. Ingestion & Validation Rules
1. **Schema Validation:** Ingestion drops or flags any observation missing required fields (`event_id`, `bus_id`, `timestamp`, `latitude`, `longitude`, `event_type`, `confidence`).
2. **Confidence Filtering:** Observations with `confidence < 0.50` are quarantined for validation rather than triggering immediate map alerts.
3. **Evidence Hygiene:** Base64 binary strings are prohibited in perception events; media must be uploaded to object storage first, and the resulting `evidence_uri` passed in the event payload.
