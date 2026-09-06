# API Contract

## 1. Principles
- **Base URL:** `/api/v1`
- **Format:** JSON over HTTPS for REST; JSON frames over WSS for WebSocket.
- **Timestamps:** ISO-8601 with explicit timezone offset (`YYYY-MM-DDTHH:mm:ssZ` or `YYYY-MM-DDTHH:mm:ss+05:30`).
- **Identifiers:** Stable string IDs (`event_id`, `segment_id`, `bus_id`, `incident_id`).
- **Coordinate Standard:** GeoJSON format `[longitude, latitude]` for all API exchanges. The frontend transforms to Google Maps `{lat, lng}` only at rendering boundaries.
- **Contract Changes:** Any breaking change must update this document and all affected consumers simultaneously.

---

## 2. REST Endpoints

### 2.1 Road Segments GeoJSON
- **Endpoint:** `GET /api/v1/segments/geojson`
- **Description:** Returns the complete road network with current aggregate condition scores.
- **Response Schema:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": "seg_chandigarh_001",
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [76.7794, 30.7333],
          [76.7820, 30.7350]
        ]
      },
      "properties": {
        "segment_id": "seg_chandigarh_001",
        "name": "Jan Marg (Sector 16 to 17)",
        "condition_score": 85.5,
        "confidence": 0.92,
        "pothole_count": 0,
        "waterlogging_count": 0,
        "observation_count": 14,
        "last_updated": "2026-08-31T14:30:00+05:30"
      }
    }
  ]
}
```

### 2.2 Road Segment Details & History
- **Endpoint:** `GET /api/v1/segments/{segment_id}`
- **Endpoint:** `GET /api/v1/segments/{segment_id}/history`
- **History Response Schema:**
```json
[
  {
    "timestamp": "2026-08-20T10:00:00+05:30",
    "condition_score": 92.0,
    "confidence": 0.88,
    "pothole_count": 0,
    "bus_id": "BUS-101"
  },
  {
    "timestamp": "2026-08-31T14:30:00+05:30",
    "condition_score": 85.5,
    "confidence": 0.92,
    "pothole_count": 1,
    "bus_id": "BUS-104"
  }
]
```

### 2.3 Events
- **Endpoint:** `GET /api/v1/events`
- **Query Parameters:** `event_type`, `road_segment_id`, `min_severity`, `limit`, `offset`
- **Response Schema:**
```json
[
  {
    "event_id": "evt_pot_001",
    "bus_id": "BUS-102",
    "timestamp": "2026-08-31T15:20:10+05:30",
    "latitude": 30.7333,
    "longitude": 76.7794,
    "road_segment_id": "seg_chandigarh_001",
    "event_type": "road_defect",
    "class_name": "pothole",
    "confidence": 0.89,
    "severity": 3,
    "risk_score": 78.5,
    "risk_level": "High",
    "breadth_cm": 44.5,
    "depth_cm": 6.8,
    "dimensions": {
      "breadth_cm": 44.5,
      "depth_cm": 6.8,
      "area_sq_cm": 665.0
    },
    "risk_assessment": "Severe pothole (6.8cm depth, 44.5cm breadth): High risk of wheel rim and suspension damage.",
    "frame_id": 4120,
    "evidence_uri": "http://localhost:8000/evidence/evt_pot_001.jpg"
  }
]
```

### 2.4 Incidents
- **Endpoint:** `GET /api/v1/incidents`
- **Response Schema:**
```json
[
  {
    "incident_id": "inc_001",
    "timestamp": "2026-08-31T16:05:00+05:30",
    "latitude": 30.7350,
    "longitude": 76.7820,
    "incident_type": "illegal_parking",
    "severity": 2,
    "vehicle_track_id": "trk_901",
    "plate_text": "CH01AB1234",
    "plate_confidence": 0.94,
    "evidence_uri": "http://localhost:8000/evidence/inc_001.jpg"
  }
]
```

### 2.5 Bus Telemetry
- **Endpoint:** `GET /api/v1/buses`
- **Response Schema:**
```json
[
  {
    "bus_id": "BUS-101",
    "latitude": 30.7345,
    "longitude": 76.7801,
    "heading_deg": 142.5,
    "timestamp": "2026-08-31T16:15:00+05:30"
  }
]
```

### 2.6 City Analytics Summary
- **Endpoint:** `GET /api/v1/analytics/summary`
- **Description:** Returns aggregate KPI numbers, condition tier distribution, and active alerts across the entire city.
- **Response Schema:**
```json
{
  "total_road_segments": 42,
  "monitored_buses": 8,
  "critical_defects": 5,
  "active_incidents": 3,
  "average_city_health": 81.4,
  "condition_distribution": {
    "good": 28,
    "moderate": 9,
    "poor": 3,
    "critical": 2
  },
  "last_updated": "2026-09-04T12:00:00+05:30"
}
```

---

## 3. Ingestion & Edge Video Processing Endpoints

### 3.1 Structured Observation Ingestion
- **Endpoint:** `POST /api/v1/ingest/observation`
- **Body Schema:** Conforms to `ObservationEvent` model ([AI_CONTRACT.md](AI_CONTRACT.md)).
- **Response Schema:**
```json
{
  "status": "ok",
  "event_id": "evt_20260904_101_0042",
  "matched_segment": "seg_chandigarh_001"
}
```

### 3.2 Bus Telemetry Ingestion
- **Endpoint:** `POST /api/v1/ingest/telemetry`
- **Body Schema:** Conforms to `BusTelemetry` model.
- **Response Schema:**
```json
{
  "status": "ok",
  "bus_id": "BUS-101"
}
```

### 3.3 Traffic Incident Ingestion
- **Endpoint:** `POST /api/v1/ingest/incident`
- **Body Schema:** Conforms to `Incident` model.
- **Response Schema:**
```json
{
  "status": "ok",
  "incident_id": "inc_001"
}
```

### 3.4 Video Processing Pipeline Trigger
- **Endpoint:** `POST /api/v1/ingest/video/process`
- **Content-Type:** `multipart/form-data`
- **Form Parameters:**
  - `bus_id` (string, default: `"BUS-101"`)
  - `use_sample` (boolean, default: `false`)
  - `show_window` (boolean, default: `true` — opens desktop OpenCV HUD window)
  - `enabled_detectors` (JSON string, e.g. `'{"road_defect": true, "waterlogging": true, "traffic": true, "incident": true}'`)
  - `video_file` (file upload, optional if `use_sample=true`)
  - `gps_file` (file upload, optional)
- **Supported Video Containers:** `.mp4`, `.avi`, `.mkv`, `.mov`, `.h264`, `.h265`, `.mjpeg`, `.ts`, `.raw`, `.flv`, `.webm`
- **Response Schema:**
```json
{
  "status": "processing_started",
  "bus_id": "BUS-101",
  "video_path": "backend/static/uploads/dashcam_01.mp4",
  "gps_path": "backend/static/uploads/gps_01.json",
  "show_window": true,
  "enabled_detectors": {
    "road_defect": true,
    "waterlogging": true,
    "traffic": true,
    "incident": true
  }
}
```

### 3.5 Video Processing Pipeline Status
- **Endpoint:** `GET /api/v1/ingest/video/status`
- **Response Schema:**
```json
{
  "is_running": true,
  "progress": 45.2,
  "current_frame": 452,
  "total_frames": 1000,
  "status_message": "Processing frame 452/1000 (45.2%)",
  "last_result": null
}
```

### 3.6 Static Evidence Files
- **Endpoint:** `GET /evidence/{filename}`
- **Description:** Serves cropped keyframe JPEG evidence images and video clip artifacts saved in `backend/static/evidence/`.

---

## 4. WebSocket Protocol (`/ws/live`)

The WebSocket endpoint broadcasts live event streams to connected clients.

### 4.1 Live Bus Telemetry Frame
```json
{
  "type": "BUS_TELEMETRY",
  "payload": {
    "bus_id": "BUS-101",
    "latitude": 30.7348,
    "longitude": 76.7805,
    "heading_deg": 145.0,
    "timestamp": "2026-08-31T16:15:05+05:30"
  }
}
```

### 4.2 Live Event Frame
```json
{
  "type": "NEW_EVENT",
  "payload": {
    "event_id": "evt_pot_002",
    "bus_id": "BUS-103",
    "timestamp": "2026-08-31T16:15:10+05:30",
    "latitude": 30.7360,
    "longitude": 76.7830,
    "road_segment_id": "seg_chandigarh_002",
    "event_type": "road_defect",
    "class_name": "pothole",
    "confidence": 0.91,
    "severity": 2,
    "evidence_uri": "http://localhost:8000/evidence/evt_pot_002.jpg"
  }
}
```

### 4.3 Live Incident Frame
```json
{
  "type": "NEW_INCIDENT",
  "payload": {
    "incident_id": "inc_002",
    "bus_id": "BUS-101",
    "timestamp": "2026-08-31T16:15:15+05:30",
    "latitude": 30.7355,
    "longitude": 76.7810,
    "incident_type": "rash_driving",
    "severity": 4,
    "vehicle_track_id": "trk_402",
    "plate_text": "PB65AB1234",
    "plate_confidence": 0.92,
    "evidence_uri": "http://localhost:8000/evidence/inc_002.jpg"
  }
}
```

### 4.4 Segment Condition Update Frame
```json
{
  "type": "SEGMENT_UPDATE",
  "payload": {
    "type": "Feature",
    "id": "seg_chandigarh_001",
    "geometry": {
      "type": "LineString",
      "coordinates": [[76.7794, 30.7333], [76.7820, 30.7350]]
    },
    "properties": {
      "segment_id": "seg_chandigarh_001",
      "name": "Jan Marg (Sector 16 to 17)",
      "condition_score": 83.2,
      "confidence": 0.94,
      "pothole_count": 1,
      "waterlogging_count": 0,
      "observation_count": 15,
      "last_updated": "2026-08-31T16:15:10+05:30"
    }
  }
}
```

---

## 5. Error Response Schema
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Road segment with ID 'seg_999' was not found.",
    "timestamp": "2026-08-31T16:15:12+05:30"
  }
}
```
