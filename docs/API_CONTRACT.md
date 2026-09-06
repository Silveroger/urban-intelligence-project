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
> [!NOTE]
> All segment geometries returned by `/api/v1/segments/geojson` are OSM-derived canonical road centerlines (EPSG:4326 WGS84) with 13 to 38 vertices per segment, matching genuine Chandigarh road corridors.
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
          [76.7820, 30.7350],
          [76.7845, 30.7370],
          [76.7870, 30.7390]
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
      [76.7820, 30.7350],
      [76.7845, 30.7370],
      [76.7870, 30.7390]
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
    "incident_score": 50.0,
    "vehicle_track_id": "trk_901",
    "plate_text": "CH01AB1234",
    "plate_confidence": 0.94,
    "latitude": 30.7350,
    "longitude": 76.7820,
    "timestamp": "2026-08-31T16:05:00+05:30",
    "road_segment_id": "seg_chandigarh_001",
    "observation_id": null,
    "evidence_uri": "https://[PROJECT-REF].supabase.co/storage/v1/object/sign/road-evidence/uploads/inc_001.mp4?token=...",
    "description": "Vehicle blocking bus bay corridor",
    "status": "open"
  }
]
```
> [!NOTE]
> `incident_score` is computed deterministically as `round(severity * 25.0, 1)`. `evidence_uri` is dynamically generated as a 1-hour signed URL from Supabase Storage (`road-evidence` bucket) upon response serialization.

### 2.6 Bus Fleet Telemetry
- **Endpoint:** `GET /api/v1/buses`
- **Endpoint:** `POST /api/v1/telemetry`
- **Response Schema:**
```json
[
  {
    "bus_id": "b78b87ce-880d-4560-bf8c-1ff43f324630",
    "vehicle_number": "CH01-GA-3412",
    "latitude": 30.7345,
    "longitude": 76.7801,
    "heading_deg": 142.5,
    "timestamp": "2026-08-31T16:15:00+05:30",
    "status": "active"
  }
]
```

### 2.7 City Infrastructure Analytics Summary
- **Endpoint:** `GET /api/v1/analytics/summary`
- **Description:** Returns high-level citywide infrastructure health, defect counts, active fleet, and condition distribution tiers.
- **Response Schema:**
```json
{
  "total_segments": 11,
  "average_condition_score": 72.8,
  "critical_segments_count": 0,
  "active_buses_count": 11,
  "total_events_count": 20,
  "total_incidents_count": 7,
  "condition_distribution": {
    "healthy": 6,
    "moderate": 5,
    "poor": 0,
    "critical": 0
  }
}
```

---

## 3. WebSocket Protocol (`/ws/live`)

The live streaming endpoint `/ws/live` broadcasts real-time telemetry, defect events, incidents, and segment metric changes.

### 3.1 Client Heartbeat (Ping / Pong)
- Client sends: `"ping"`
- Server responds: `{"type": "PONG"}`

### 3.2 Live Bus Telemetry Frame (`BUS_TELEMETRY`)
Broadcast upon receiving vehicle GPS coordinates via `POST /api/v1/telemetry`:
```json
{
  "type": "BUS_TELEMETRY",
  "payload": {
    "bus_id": "CH01-GA-3412",
    "latitude": 30.7348,
    "longitude": 76.7805,
    "heading_deg": 145.0,
    "timestamp": "2026-08-31T16:15:05+05:30",
    "status": "active"
  }
}
```

### 3.3 Live Defect Event Frame (`NEW_EVENT`)
Broadcast when an AI observation with `confidence >= 0.50` is confirmed:
```json
{
  "type": "NEW_EVENT",
  "payload": {
    "event_id": "evt_pot_002",
    "bus_id": "CH01-GA-3412",
    "timestamp": "2026-08-31T16:15:10+05:30",
    "latitude": 30.7360,
    "longitude": 76.7830,
    "road_segment_id": "seg_chandigarh_002",
    "event_type": "road_defect",
    "class_name": "pothole",
    "confidence": 0.91,
    "severity": 2,
    "severity_label": "moderate",
    "evidence_uri": "https://[PROJECT-REF].supabase.co/storage/v1/object/sign/road-evidence/uploads/evt_pot_002.jpg?token=..."
  }
}
```

### 3.4 Live Incident Frame (`NEW_INCIDENT`)
Broadcast immediately when a new traffic violation/incident is created:
```json
{
  "type": "NEW_INCIDENT",
  "payload": {
    "incident_id": "inc_20260831_001",
    "incident_type": "illegal_parking",
    "severity": 2,
    "severity_label": "moderate",
    "incident_score": 50.0,
    "vehicle_track_id": "trk_901",
    "plate_text": "CH01AB1234",
    "plate_confidence": 0.94,
    "latitude": 30.7350,
    "longitude": 76.7820,
    "timestamp": "2026-08-31T16:15:11+05:30",
    "road_segment_id": "seg_chandigarh_001",
    "observation_id": null,
    "evidence_uri": "https://[PROJECT-REF].supabase.co/storage/v1/object/sign/road-evidence/uploads/inc_001.jpg?token=...",
    "description": "Vehicle blocking bus bay corridor",
    "status": "open"
  }
}
```

### 3.5 Live Segment Update Frame (`SEGMENT_UPDATE`)
Broadcast whenever a road segment's metrics are recalculated:
```json
{
  "type": "SEGMENT_UPDATE",
  "payload": {
    "segment_id": "seg_chandigarh_001",
    "condition_score": 85.5,
    "pothole_count": 1,
    "waterlogging_count": 0,
    "observation_count": 15,
    "last_updated": "2026-08-31T16:15:15+05:30"
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

| Error Code | HTTP Status | Description & Triggers |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Request body or query parameters failed validation (e.g. `plate_text` provided without `plate_confidence`, invalid coordinates). |
| `RESOURCE_NOT_FOUND` | 404 | Requested entity identifier does not exist. |
| `DATABASE_CONNECTION_ERROR`| 503 | Database connection unavailable, pooler timeout, or operational query failure. Zero secrets or stack traces leaked. |
| `BAD_REQUEST` | 400 | Malformed request syntax or unparseable headers. |
| `INTERNAL_SERVER_ERROR` | 500 | Uncaught application exception safely formatted without diagnostics leaks. |
