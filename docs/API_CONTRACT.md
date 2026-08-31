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
    "class_name": "pothole_deep",
    "confidence": 0.89,
    "severity": 3,
    "frame_id": 4120,
    "evidence_uri": "https://storage.urban-intel.city/frames/evt_pot_001.jpg"
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
    "evidence_uri": "https://storage.urban-intel.city/clips/inc_001.mp4"
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

---

## 3. WebSocket Protocol (`/ws/live`)

### 3.1 Live Bus Telemetry Frame
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

### 3.2 Live Event Frame
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
    "evidence_uri": "https://storage.urban-intel.city/frames/evt_pot_002.jpg"
  }
}
```

---

## 4. Error Response Schema
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Road segment with ID 'seg_999' was not found.",
    "timestamp": "2026-08-31T16:15:12+05:30"
  }
}
```
