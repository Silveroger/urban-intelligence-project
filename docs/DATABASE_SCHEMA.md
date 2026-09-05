# Database Schema & Spatial Contract

## 1. Overview
The persistent data store for the platform is **PostgreSQL (15+)** with the **PostGIS (3.3+)** extension enabled. 
In Supabase, PostGIS spatial functions are provisioned under the **`gis` schema** (e.g. `gis.ST_MakePoint`, `gis.ST_DWithin`, `gis.ST_Distance`, `gis.ST_AsGeoJSON`). Spatial geometries are stored using SRID `4326` (WGS84).

---

## 2. Core Relational & Spatial Entities

```text
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     buses       │◄──────│   gps_points    │       │     routes      │
└────────┬────────┘       └─────────────────┘       └─────────────────┘
         │
         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  observations   │──────►│  road_segments  │◄──────│ segment_history │
└────────┬────────┘       └────────┬────────┘       └─────────────────┘
         │                         │
         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐
│    evidence     │       │    incidents    │
│ (Supabase S3)   │       └─────────────────┘
└─────────────────┘
```

---

## 3. Canonical Entity Definitions

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
    bus_id VARCHAR(64) REFERENCES buses(bus_id) ON DELETE SET NULL,
    segment_id VARCHAR(64) REFERENCES road_segments(segment_id) ON DELETE SET NULL,
    geom GEOMETRY(Point, 4326) NOT NULL,
    event_type VARCHAR(32) NOT NULL, -- road_defect, waterlogging, traffic, incident
    class_name VARCHAR(64),
    confidence NUMERIC(3, 2) NOT NULL,
    severity SMALLINT CHECK (severity BETWEEN 1 AND 4),
    evidence_uri VARCHAR(512),
    observed_at TIMESTAMPTZ NOT NULL,
    metadata JSONB,
    status VARCHAR(32) DEFAULT 'confirmed', -- confirmed or quarantined
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
    segment_id VARCHAR(64) REFERENCES road_segments(segment_id) ON DELETE CASCADE,
    condition_score NUMERIC(5, 2) NOT NULL,
    confidence NUMERIC(3, 2) NOT NULL DEFAULT 1.00,
    pothole_count INTEGER NOT NULL DEFAULT 0,
    waterlogging_count INTEGER NOT NULL DEFAULT 0,
    bus_id VARCHAR(64),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
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
    last_latitude DOUBLE PRECISION,
    last_longitude DOUBLE PRECISION,
    last_ping TIMESTAMPTZ
);

CREATE TABLE gps_points (
    point_id BIGSERIAL PRIMARY KEY,
    bus_id VARCHAR(64) REFERENCES buses(bus_id) ON DELETE CASCADE,
    geom GEOMETRY(Point, 4326) NOT NULL,
    heading_deg NUMERIC(5, 2),
    speed_kmh DOUBLE PRECISION,
    accuracy_meters DOUBLE PRECISION,
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
    road_segment_id VARCHAR(64) REFERENCES road_segments(segment_id) ON DELETE SET NULL,
    observation_id VARCHAR(64) REFERENCES observations(observation_id) ON DELETE SET NULL,
    geom GEOMETRY(Point, 4326) NOT NULL,
    incident_type VARCHAR(64) NOT NULL,
    severity SMALLINT DEFAULT 1 CHECK (severity BETWEEN 1 AND 4),
    vehicle_track_id VARCHAR(64),
    plate_text VARCHAR(32),
    plate_confidence NUMERIC(3, 2),
    evidence_uri VARCHAR(512),
    description VARCHAR(512),
    status VARCHAR(32) DEFAULT 'open',
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_incidents_geom ON incidents USING GIST (geom);
```

---

## 4. Production Schema Reconciliation Strategy

The initial Supabase database was provisioned with legacy column names (`id UUID`, `road_name`, `health_score`, `geometry`, `location`, `observation_type`, `detected_at`, `evidence_path`).

To safely transition live tables to the canonical contract without data loss:
1. **Authoritative Migration Script:** Execute [`backend/scripts/migrate_to_documented_schema.sql`](../backend/scripts/migrate_to_documented_schema.sql) in the Supabase SQL Editor.
2. **Safety Guarantees:**
   - Entire migration runs in a single transactional block (`BEGIN ... COMMIT`).
   - Legacy columns and UUIDs are non-destructively preserved as auxiliary fields.
   - Preflight assertions verify existing row counts, foreign key constraints, and PostGIS geometry validity.
   - Auto-incrementing sequences are reset to `MAX(id) + 1`.
3. **Known Schema Discrepancies:** Tracked in [`docs/BUGS_AND_DISCREPANCIES.md`](BUGS_AND_DISCREPANCIES.md).
