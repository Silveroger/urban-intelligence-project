# Database Schema & Spatial Contract

## 1. Overview
The persistent data store for the platform is **PostgreSQL (15+)** with the **PostGIS (3.3+)** extension enabled. Spatial geometries are stored using SRID `4326` (WGS84).

---

## 2. Core Relational & Spatial Entities

```text
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     buses       │◄──────│     trips       │──────►│     routes      │
└────────┬────────┘       └────────┬────────┘       └─────────────────┘
         │                         │
         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   gps_points    │       │  observations   │──────►│  road_segments  │
└─────────────────┘       └────────┬────────┘       └────────┬────────┘
                                   │                         │
                                   ▼                         ▼
                          ┌─────────────────┐       ┌─────────────────┐
                          │    evidence     │       │ segment_history │
                          └─────────────────┘       └─────────────────┘
```

---

## 3. Entity Definitions

### 3.1 `road_segments`
Stores canonical city road network centerlines and current aggregate condition metrics.
```sql
CREATE TABLE road_segments (
    segment_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255),
    geom GEOMETRY(LineString, 4326) NOT NULL,
    condition_score NUMERIC(5, 2) DEFAULT 100.00,
    confidence NUMERIC(3, 2) DEFAULT 1.00,
    pothole_count INTEGER DEFAULT 0,
    waterlogging_count INTEGER DEFAULT 0,
    observation_count INTEGER DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_road_segments_geom ON road_segments USING GIST (geom);
```

### 3.2 `observations`
Stores validated detections emitted by edge AI and sensing fleet vehicles.
```sql
CREATE TABLE observations (
    observation_id VARCHAR(64) PRIMARY KEY,
    bus_id VARCHAR(64) REFERENCES buses(bus_id),
    segment_id VARCHAR(64) REFERENCES road_segments(segment_id),
    geom GEOMETRY(Point, 4326) NOT NULL,
    event_type VARCHAR(32) NOT NULL, -- road_defect, waterlogging, traffic, incident
    class_name VARCHAR(64),
    confidence NUMERIC(3, 2) NOT NULL,
    severity SMALLINT CHECK (severity BETWEEN 1 AND 4),
    evidence_uri VARCHAR(512),
    observed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_observations_geom ON observations USING GIST (geom);
CREATE INDEX idx_observations_segment ON observations(segment_id);
CREATE INDEX idx_observations_observed_at ON observations(observed_at);
```

### 3.3 `segment_history`
Stores historical passes and longitudinal condition trends for each road segment.
```sql
CREATE TABLE segment_history (
    history_id BIGSERIAL PRIMARY KEY,
    segment_id VARCHAR(64) REFERENCES road_segments(segment_id),
    condition_score NUMERIC(5, 2) NOT NULL,
    confidence NUMERIC(3, 2) NOT NULL,
    pothole_count INTEGER NOT NULL,
    waterlogging_count INTEGER NOT NULL,
    bus_id VARCHAR(64),
    recorded_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX idx_segment_history_segment_time ON segment_history(segment_id, recorded_at DESC);
```

### 3.4 `buses` & `gps_points`
Stores fleet vehicle registration and high-frequency location traces.
```sql
CREATE TABLE buses (
    bus_id VARCHAR(64) PRIMARY KEY,
    vehicle_number VARCHAR(32),
    route_id VARCHAR(64),
    status VARCHAR(32) DEFAULT 'active',
    last_ping TIMESTAMPTZ
);

CREATE TABLE gps_points (
    point_id BIGSERIAL PRIMARY KEY,
    bus_id VARCHAR(64) REFERENCES buses(bus_id),
    geom GEOMETRY(Point, 4326) NOT NULL,
    heading_deg NUMERIC(5, 2),
    recorded_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX idx_gps_points_geom ON gps_points USING GIST (geom);
CREATE INDEX idx_gps_points_bus_time ON gps_points(bus_id, recorded_at DESC);
```

### 3.5 `incidents`
Stores traffic violations, obstructions, and vehicle tracking data.
```sql
CREATE TABLE incidents (
    incident_id VARCHAR(64) PRIMARY KEY,
    geom GEOMETRY(Point, 4326) NOT NULL,
    incident_type VARCHAR(64) NOT NULL,
    severity SMALLINT DEFAULT 1,
    vehicle_track_id VARCHAR(64),
    plate_text VARCHAR(32),
    plate_confidence NUMERIC(3, 2),
    evidence_uri VARCHAR(512),
    recorded_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX idx_incidents_geom ON incidents USING GIST (geom);
```

---

## 4. Ownership & Migration Rules
- **Backend/Geospatial Owner:** Butar maintains all DDL migrations, PostGIS spatial indexing, and aggregation views.
- **Frontend Boundary:** The dashboard never connects directly to PostgreSQL/PostGIS. All interactions occur strictly through REST API endpoints and WebSocket messages.
