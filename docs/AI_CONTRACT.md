# AI Perception Output Contract

## 1. Overview
This document specifies the structured JSON schema that edge and cloud perception models must produce. The backend ingestion service validates all inference outputs against these contracts before spatial aggregation and persistence.

---

## 2. Structured Perception Observation Schema

Each perception event produced by computer vision models must conform to the following schema:

| Field | Type | Required | Description |
|---|---|---|---|
| `event_id` | `string` | Yes | Unique deterministic identifier (e.g., `evt_20260904_101_0042`). |
| `bus_id` | `string` | Yes | Identifier of the sensing fleet vehicle capturing the frame. |
| `timestamp` | `string` (ISO-8601) | Yes | Frame capture timestamp with timezone (e.g., `2026-09-04T15:20:10+05:30`). |
| `latitude` | `number` | Yes | WGS84 latitude of the detection camera/GPS position. |
| `longitude` | `number` | Yes | WGS84 longitude of the detection camera/GPS position. |
| `road_segment_id` | `string` | Optional | Matched road segment ID if edge map-matching was executed. |
| `event_type` | `enum` | Yes | One of: `"road_defect"`, `"waterlogging"`, `"traffic"`, `"incident"`, `"infrastructure"`, `"pedestrian"`. |
| `class_name` | `string` | Optional | Specific perception class (see Section 3). |
| `confidence` | `number` ($0.0-1.0$) | Yes | Model prediction confidence score. |
| `severity` | `integer` ($1-4$) | Optional | Severity rating: $1$ (Minor), $2$ (Moderate), $3$ (Severe), $4$ (Critical). |
| `bbox` | `array[number]` | Optional | Bounding box coordinates `[x1, y1, x2, y2]` in pixel coordinates. |
| `frame_id` | `integer` | Optional | Video stream sequence frame number. |
| `track_id` | `string` / `integer` | Optional | Persistent tracking ID for dynamic objects (e.g., vehicles). |
| `plate_text` | `string` | Optional | License plate string detected via OCR. |
| `plate_confidence`| `number` ($0.0-1.0$) | Optional | OCR confidence score for the detected plate text. |
| `evidence_uri` | `string` (URI) | Optional | URL or storage path to the cropped evidence image or video artifact. |

---

## 3. Modular Detector Categories & Classes

### 3.1 Road Defect Detection (`road_defect`)
- **Module:** `ai/detectors/road_defect_detector.py`
- **Classes:** `"pothole"`, `"damaged_road"`, `"major_crack"`, `"surface_wear"`.
- **Severity Criteria:**
  - $1$ (Minor): Small surface crack, surface wear < 15% bounding area.
  - $2$ (Moderate): Single shallow pothole or linear fissure.
  - $3$ (Severe): Deep pothole with prominent rim shadows or multi-branch alligator cracking.
  - $4$ (Critical): Multiple large continuous potholes spanning driving lane.
- **Evidence:** Cropped, high-resolution keyframe centered on the defect with highlighted bounding box.

### 3.2 Waterlogging Detection (`waterlogging`)
- **Classes:** `"waterlogging"`, `"water_patch"`, `"submerged_lane"`.
- **Severity Criteria:**
  - $1-2$: Surface puddle / minor water patch not impeding transit flow.
  - $3-4$: Deep or extensive waterlogging submerging kerbs or entire lanes.

### 3.3 Infrastructure Deficiencies (`infrastructure`)
- **Module:** `ai/detectors/infrastructure_detector.py`
- **Classes:** `"missing_divider"`, `"missing_zebra_crossing"`, `"damaged_signboard"`, `"faded_lane_marking"`.
- **Severity:** Reflects municipal compliance deficit and pedestrian risk.

### 3.4 Pedestrian Safety Detection (`pedestrian`)
- **Module:** `ai/detectors/pedestrian_detector.py`
- **Classes:** `"vulnerable_pedestrian_crossing"`, `"pedestrian_in_danger"`.
- **Criteria:** Triggered when pedestrians are detected crossing active roadway corridors away from designated crossings.

### 3.5 Traffic Density & Flow (`traffic`)
- **Module:** `ai/detectors/traffic_density_detector.py`
- **Classes:** `"traffic_density"`, `"congestion_cluster"`.
- **Attributes:** Outputs vehicle count, occupancy ratio, and density index ($0.0-1.0$).

### 3.6 Vehicle Tracking, Incidents & OCR (`incident`)
- **Modules:** `ai/tracker/vehicle_tracker.py`, `ai/detectors/plate_recognizer.py`
- **Classes:** `"rash_driving"`, `"hit_and_run"`, `"illegal_parking"`, `"bus_lane_encroachment"`.
- **OCR Constraints:** `plate_text` is extracted alongside `plate_confidence`. Plate recognition is never asserted without confidence scoring.

---

## 4. Edge Pipeline Configuration & Detector Toggles

The pipeline supports selective detector execution to conserve edge compute (e.g., Raspberry Pi 5, NVIDIA Jetson Orin Nano):

```json
{
  "road_defect": true,
  "waterlogging": true,
  "traffic": true,
  "incident": true,
  "infrastructure": false,
  "pedestrian": true
}
```

- When a detector category is disabled (`false`), the corresponding inference module is skipped, reducing per-frame latency by up to 60%.

---

## 5. Supported Video Formats & Edge Optimization
- **Accepted Containers:** `.mp4`, `.avi`, `.mkv`, `.mov`, `.h264`, `.h265`, `.mjpeg`, `.ts`, `.raw`, `.flv`, `.webm`.
- **Edge Optimization (`ai/edge_optimizer.py`):**
  - ONNX Runtime export with TensorRT / CUDA execution providers.
  - INT8 dynamic post-training quantization for low-power ARM/x86 CPUs.
  - FP16 half-precision GPU inference for NVIDIA Jetson nodes.
