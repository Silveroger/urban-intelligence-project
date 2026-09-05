# API Contract

## 1. Principles
- **Base URL:** `/api/v1`
- **Format:** JSON over HTTPS for REST; JSON frames over WSS for WebSocket.
- **Timestamps:** ISO-8601 with explicit timezone offset (`YYYY-MM-DDTHH:mm:ssZ` or `YYYY-MM-DDTHH:mm:ss+05:30`).
- **Identifiers:** Stable string IDs (`event_id`, `segment_id`, `bus_id`, `incident_id`).
- **Coordinate Standard:** GeoJSON format `[longitude, latitude]` for all API exchanges. The frontend transforms to Google Maps `{lat, lng}` only at rendering boundaries.
- **Contract Changes:** Any breaking change must update this document and all affected consumers simultaneously. See [`docs/BUGS_AND_DISCREPANCIES.md`](BUGS_AND_DISCREPANCIES.md) for active interface reconciliations.

---

## 2. REST Endpoints

### 2.1 Road Segments GeoJSON
- **Endpoint:** `GET /api/v1/segments/geojson`
- **Query Parameters:**
  - `format`: Optional. `'geojson'` (default) or `'flat'`.
- **Default Response Schema (`FeatureCollection`):**
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

- **Flat Format Response Schema (`?format=flat`):**
```json
[
  {
    "segment_id": "seg_chandigarh_001",
    "name": "Jan Marg (Sector 16 to 17)",
    "geometry": [
      [76.7794, 30.7333],
      [76.7820, 30.7350]
    ],
    "condition_score": 85.5,
    "confidence": 0.92,
    "pothole_count": 0,
    "waterlogging_count": 0,
    "observation_count": 14,
    "last_updated": "2026-08-31T14:30:00+05:30"
  }
]
```

### 2.2 Road Segment Details & History
- **Endpoint:** `GET /api/v1/segments/{segment_id}`
- **Endpoint:** `GET /api/v1/segments/{segment_id}/history`
- **History Response Schema:**
```json
[
  {
    "timestamp": "2026-08-20T10:00:00+05:30",
    "date": "2026-08-20T10:00:00+05:30",
    "condition_score": 92.0,
    "score": 92.0,
    "confidence": 0.88,
    "pothole_count": 0,
    "bus_id": "BUS-101"
  },
  {
    "timestamp": "2026-08-31T14:30:00+05:30",
    "date": "2026-08-31T14:30:00+05:30",
    "condition_score": 85.5,
    "score": 85.5,
    "confidence": 0.92,
    "pothole_count": 1,
    "bus_id": "BUS-104"
  }
]
```

### 2.3 Road Events & Defect Observations
- **Endpoint:** `GET /api/v1/events`
- **Query Parameters:**
  - `event_type`: Filter by type (`road_defect`, `waterlogging`, `traffic`, `incident`).
  - `road_segment_id`: Filter by segment ID.
  - `min_severity`: Filter by minimum severity integer ($1-4$).
  - `limit`: Pagination limit (default $50$, max $200$).
  - `offset`: Pagination offset (default $0$).
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
    "severity_label": "high",
    "frame_id": 4120,
    "evidence_uri": "https://storage.urban-intel.city/frames/evt_pot_001.jpg"
  }
]
```

### 2.4 AI Observation Ingestion
- **Endpoint:** `POST /api/v1/observations`
- **Description:** Ingests AI edge perception observation. Confirms or quarantines event based on confidence threshold ($0.50$), triggers PostGIS map-matching, updates segment condition score, and broadcasts live event.
- **Request Body:** Conforms to [`docs/AI_CONTRACT.md`](AI_CONTRACT.md).
- **Response Schema:**
```json
{
  "status": "confirmed",
  "event_id": "evt_pot_001",
  "observation_id": "evt_pot_001",
  "road_segment_id": "seg_chandigarh_001",
  "quarantined": false,
  "message": "Observation confirmed, matched to segment 'seg_chandigarh_001', and broadcasted."
}
```

### 2.5 Traffic Incidents
- **Endpoint:** `GET /api/v1/incidents`
- **Endpoint:** `POST /api/v1/incidents`
- **Query Parameters:** `status` (`open`, `resolved`), `limit`, `offset`.
- **Response Schema:**
```json
[
  {
    "incident_id": "inc_001",
    "incident_type": "illegal_parking",
    "severity": 2,
    "severity_label": "moderate",
    "vehicle_track_id": "trk_901",
    "plate_text": "CH01AB1234",
    "plate_confidence": 0.94,
    "latitude": 30.7350,
    "longitude": 76.7820,
    "timestamp": "2026-08-31T16:05:00+05:30",
    "road_segment_id": "seg_chandigarh_001",
    "observation_id": null,
    "evidence_uri": "https://storage.urban-intel.city/clips/inc_001.mp4",
    "description": "Vehicle blocking bus bay corridor",
    "status": "open"
  }
]
```

### 2.6 Bus Fleet Telemetry
- **Endpoint:** `GET /api/v1/buses`
- **Endpoint:** `POST /api/v1/telemetry`
- **Response Schema:**
```json
[
  {
    "bus_id": "BUS-101",
    "latitude": 30.7345,
    "longitude": 76.7801,
    "heading_deg": 142.5,
    "timestamp": "2026-08-31T16:15:00+05:30",
    "status": "active"
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
    "timestamp": "2026-08-31T16:15:05+05:30",
    "status": "active"
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
    "severity_label": "moderate",
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

| Error Code | HTTP Status | Description |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Request body or query parameters failed schema validation. |
| `RESOURCE_NOT_FOUND` | 404 | Requested entity identifier does not exist. |
| `DATABASE_CONNECTION_ERROR`| 503 | Database connection pool unavailable or query timeout. |
| `INTERNAL_SERVER_ERROR` | 500 | Uncaught server exception. |
