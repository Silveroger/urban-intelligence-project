# Database Schema & Spatial Contract

## 1. Overview
The persistent data store for the platform is **PostgreSQL 17.6** with the **PostGIS 3.3.7** extension enabled on Supabase cloud infrastructure. 
PostGIS spatial functions and geometry types reside in the **`gis` schema** (e.g. `gis.ST_MakePoint`, `gis.ST_DWithin`, `gis.ST_Distance`, `gis.ST_AsGeoJSON`). Geometries use SRID `4326` (WGS84).
The backend async engine connects with `search_path: public, gis` to ensure transparent PostGIS type and function resolution.

All spatial coordinates at database and API boundaries strictly adhere to the **GeoJSON Standard: `[longitude, latitude]`**.

---

## 2. Core Relational & Spatial Entities

```text
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     routes      │◄──────│     trips       │──────►│     buses       │
└─────────────────┘       └─────────────────┘       └────────┬────────┘
                                                             │
                                                             ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  gps_records    │       │   gps_points    │◄──────│  observations   │
│  (Compat View)  │◄─ ─ ─ │(Physical Table) │       └────────┬────────┘
└─────────────────┘       └─────────────────┘                │
                                                             ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ segment_history │──────►│  road_segments  │◄──────│    incidents    │
└─────────────────┘       └─────────────────┘       └────────┬────────┘
                                                             │
                                                             ▼
                                                    ┌─────────────────┐
                                                    │    evidence     │
                                                    │ (Supabase S3)   │
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

> [!IMPORTANT]
> **OSM-Derived Canonical Road Geometries:**  
> The `geom` column stores authentic OpenStreetMap-derived road centerlines (`backend/data/chandigarh_roads_canonical.geojson`) using SRID 4326 (WGS84). Each segment contains 13 to 38 vertices following the genuine curvature of Chandigarh's arterial corridors. Do **NOT** replace these with coarse synthetic 2-to-4 point straight lines. Bus GPS traces, defect observations, and traffic incidents are snapped to and traverse along these canonical geometries.

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
    metadata JSONB, -- Stores AI diagnostic metrics (risk_score, breadth_cm, depth_cm, dimensions, risk_assessment)
    status VARCHAR(32) DEFAULT 'confirmed', -- confirmed or quarantined
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_observations_geom ON observations USING GIST (geom);
CREATE INDEX idx_observations_segment ON observations(segment_id);
CREATE INDEX idx_observations_observed_at ON observations(observed_at);
```

### 3.3 `segment_history`
Stores historical passes and longitudinal condition trends for each road segment (debounced to 10s intervals).
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

### 3.4 `buses` & `routes` & `trips`
Stores fleet vehicle registration, transit routes, and active trips.
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

CREATE TABLE routes (
    route_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE trips (
    trip_id VARCHAR(64) PRIMARY KEY,
    bus_id VARCHAR(64) REFERENCES buses(bus_id) ON DELETE CASCADE,
    route_id VARCHAR(64) REFERENCES routes(route_id) ON DELETE SET NULL,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    status VARCHAR(32) DEFAULT 'scheduled'
);
```

### 3.5 GPS Architecture: `gps_points` & `gps_records`
High-frequency vehicle position tracking.

```sql
-- Authoritative Physical Source-of-Truth Table:
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

-- Non-Destructive Backward-Compatibility VIEW:
CREATE OR REPLACE VIEW gps_records AS 
SELECT * FROM gps_points;
```

> [!WARNING]
> **CRITICAL ARCHITECTURAL DIRECTIVE (DO NOT FORK GPS PIPELINES):**  
> `public.gps_points` is the physical table that holds all telemetry traces. `public.gps_records` is a zero-overhead compatibility VIEW over `gps_points`.  
> Future developers and AI agents must **NEVER** create a separate `gps_records` table, migrate physical storage away from `gps_points`, or build a second competing telemetry ingestion pipeline. All raw telemetry inserts write to `gps_points`.

### 3.6 `incidents`
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
CREATE INDEX idx_incidents_observation_id ON incidents(observation_id);
CREATE INDEX idx_incidents_road_segment_id ON incidents(road_segment_id);
```

### 3.7 `evidence` (Supabase Storage Object Store)
Evidence media assets (pothole crops, incident frames) are persisted in the private Supabase Storage bucket **`road-evidence`**.
- Storage paths are clean identifiers: `uploads/<filename>`.
- API serializers generate dynamic 1-hour signed URLs via `get_signed_evidence_url(storage_path)` upon request, ensuring URLs never permanently expire in database rows.

---

## 4. Production Schema Reconciliation & Migration History

The live database was reconciled from an initial 6-table legacy state without data loss:
1. **Executed Migration Script:** [`backend/scripts/migrate_to_documented_schema.sql`](../backend/scripts/migrate_to_documented_schema.sql) applied canonical primary keys (`bus_id`, `segment_id`, `observation_id`, `incident_id`), created `routes`, `trips`, and the `gps_records` view, and re-established verified foreign keys and GiST spatial indexes.
2. **Legacy NOT NULL Constraints Dropped:** Standalone script [`backend/scripts/drop_legacy_notnull.py`](../backend/scripts/drop_legacy_notnull.py) was executed to drop NOT NULL constraints on superseded legacy columns (`legacy_bus_id`, `latitude`, `longitude`, `location`, `legacy_severity`, `detected_at`, `observation_type`, `geometry`, `road_segment_id`), and added the canonical `observations.status` column.
3. **Canonical Road Geometry Update:** Loaded authentic OpenStreetMap-derived centerlines from [`backend/data/chandigarh_roads_canonical.geojson`](../backend/data/chandigarh_roads_canonical.geojson) into `public.road_segments.geom` via [`backend/scripts/seed_chandigarh_demo.py`](../backend/scripts/seed_chandigarh_demo.py). Replaced coarse 2-to-4 point synthetic lines with 13-to-38 vertex WGS84 LineStrings strictly following real street corridors.
4. **Live Verification:** 6 real database integration tests in `backend/tests/test_integration_real.py` pass against live Supabase, validating all 9 canonical entities, PostGIS distance queries, and `gps_records` view parity.
