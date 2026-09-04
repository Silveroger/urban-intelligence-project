# Database Schema & Spatial Contract

## 1. Overview
The SIH 26124 platform supports a dual-tier persistence architecture:
1. **Cloud Persistence & Realtime Streaming (Supabase / PostgreSQL 15+ with PostGIS):** Manages live telemetry streams, cloud synchronization, row-level security (RLS), and live WebSocket subscriptions (`supabase_realtime`).
2. **Local / On-Premise Spatial Engine (PostgreSQL + PostGIS):** Provides high-performance GiST spatial indexing, trajectory projection, and road segment aggregation algorithms.

Geometries use the WGS84 spatial reference system (`SRID 4326`).

---

## 2. Relational & Spatial Entity Architecture

```text
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     buses       │◄──────│   gps_records   │──────►│  road_segments  │
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │                         │                         │
         ▼                         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   gps_points    │       │  observations   │──────►│ segment_history │
└─────────────────┘       └────────┬────────┘       └─────────────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │    incidents    │
                          └─────────────────┘
```

---

## 3. Supabase Cloud Schema (Production & Realtime Tier)

**Migration References:**
- `supabase/migrations/20260902_create_gps_records.sql`
- `supabase/migrations/20260904_full_sih_schema.sql`

### 3.1 `gps_records` (High-Frequency Telemetry Ingestion)
```sql
CREATE TABLE public.gps_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bus_id VARCHAR(64) NOT NULL DEFAULT 'BUS-101',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    speed DOUBLE PRECISION DEFAULT 0.0,
    heading DOUBLE PRECISION DEFAULT 0.0,
    location TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT check_latitude_range CHECK (latitude >= -90.0 AND latitude <= 90.0),
    CONSTRAINT check_longitude_range CHECK (longitude >= -180.0 AND longitude <= 180.0),
    CONSTRAINT check_speed_non_negative CHECK (speed >= 0.0)
);

CREATE INDEX idx_gps_records_timestamp ON public.gps_records (timestamp DESC);
CREATE INDEX idx_gps_records_bus_id_time ON public.gps_records (bus_id, timestamp DESC);
CREATE INDEX idx_gps_records_lat_lng ON public.gps_records (latitude, longitude);

ALTER TABLE public.gps_records ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public insert to gps_records" ON public.gps_records FOR INSERT TO anon, authenticated WITH CHECK (true);
CREATE POLICY "Allow public select from gps_records" ON public.gps_records FOR SELECT TO anon, authenticated USING (true);
```

### 3.2 `observations` (Edge AI Defect & Environmental Detections)
```sql
CREATE TABLE public.observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(128) UNIQUE NOT NULL,
    bus_id VARCHAR(64) NOT NULL DEFAULT 'BUS-101',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    class_name VARCHAR(64) NOT NULL,
    event_type VARCHAR(64) NOT NULL DEFAULT 'road_defect',
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.85,
    severity INTEGER NOT NULL DEFAULT 2,
    road_segment_id VARCHAR(64),
    bbox JSONB,
    evidence_image_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_observations_timestamp ON public.observations (timestamp DESC);
CREATE INDEX idx_observations_class ON public.observations (class_name);
CREATE INDEX idx_observations_severity ON public.observations (severity DESC);
CREATE INDEX idx_observations_segment ON public.observations (road_segment_id);

ALTER TABLE public.observations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public insert to observations" ON public.observations FOR INSERT TO anon, authenticated WITH CHECK (true);
CREATE POLICY "Allow public select from observations" ON public.observations FOR SELECT TO anon, authenticated USING (true);
```

### 3.3 `incidents` (Traffic Violations & Offending Vehicles)
```sql
CREATE TABLE public.incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id VARCHAR(128) UNIQUE NOT NULL,
    bus_id VARCHAR(64) NOT NULL DEFAULT 'BUS-101',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    incident_type VARCHAR(64) NOT NULL DEFAULT 'rash_driving',
    severity INTEGER NOT NULL DEFAULT 4,
    track_id INTEGER,
    plate_text VARCHAR(32),
    plate_confidence DOUBLE PRECISION DEFAULT 0.50,
    evidence_image_url TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_incidents_timestamp ON public.incidents (timestamp DESC);
CREATE INDEX idx_incidents_plate ON public.incidents (plate_text);

ALTER TABLE public.incidents ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public insert to incidents" ON public.incidents FOR INSERT TO anon, authenticated WITH CHECK (true);
CREATE POLICY "Allow public select from incidents" ON public.incidents FOR SELECT TO anon, authenticated USING (true);
```

### 3.4 `road_segments` (Aggregated Network Health State)
```sql
CREATE TABLE public.road_segments (
    segment_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    road_type VARCHAR(32) DEFAULT 'primary',
    condition_score DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    defect_count INTEGER NOT NULL DEFAULT 0,
    total_passes INTEGER NOT NULL DEFAULT 1,
    last_surveyed TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    geojson_geometry JSONB,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE public.road_segments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public select from road_segments" ON public.road_segments FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "Allow public insert/update road_segments" ON public.road_segments FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
```

### 3.5 Realtime Broadcast Configuration
```sql
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.gps_records;
        ALTER PUBLICATION supabase_realtime ADD TABLE public.observations;
        ALTER PUBLICATION supabase_realtime ADD TABLE public.incidents;
        ALTER PUBLICATION supabase_realtime ADD TABLE public.road_segments;
    END IF;
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
```

---

## 4. Local PostGIS Spatial Schema & History

For local deployments using direct PostGIS geometries:

### 4.1 PostGIS `road_segments`
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

### 4.2 `segment_history`
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

---

## 5. Verification & Tooling
- Run `node scripts/verify_supabase.cjs` to test database connectivity, table existence, and RLS policies from the command line.
