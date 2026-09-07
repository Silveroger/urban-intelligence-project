-- =============================================================================
-- SIH 26124: Schema Alignment & Extension Migration Script
-- Purpose: Bring existing Supabase PostgreSQL schema into alignment with
--          system requirements while preserving existing tables and data.
-- Note: PostGIS extension is installed under the `gis` schema.
-- =============================================================================

-- 1. Ensure PostGIS is accessible in the `gis` schema
CREATE SCHEMA IF NOT EXISTS gis;

-- 2. Enhance `road_segments` with tracking columns
ALTER TABLE road_segments
  ADD COLUMN IF NOT EXISTS pothole_count INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS waterlogging_count INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION DEFAULT 1.00;

-- 3. Enhance `segment_history` with missing metric columns
ALTER TABLE segment_history
  ADD COLUMN IF NOT EXISTS waterlogging_count INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION DEFAULT 1.00,
  ADD COLUMN IF NOT EXISTS bus_id UUID REFERENCES buses(id) ON DELETE SET NULL;

-- 4. Enhance `incidents` with edge AI tracking and OCR columns
ALTER TABLE incidents
  ADD COLUMN IF NOT EXISTS vehicle_track_id TEXT,
  ADD COLUMN IF NOT EXISTS plate_text TEXT,
  ADD COLUMN IF NOT EXISTS plate_confidence DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS evidence_uri TEXT;

-- 5. Enhance `observations` with optional status column for quarantined records
ALTER TABLE observations
  ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'confirmed'; -- 'confirmed' or 'quarantined'

-- 6. Ensure Spatial GiST Indexes exist (using PostGIS in `gis` schema)
CREATE INDEX IF NOT EXISTS idx_road_segments_geometry 
  ON road_segments USING GIST (geometry);

CREATE INDEX IF NOT EXISTS idx_observations_location 
  ON observations USING GIST (location);

CREATE INDEX IF NOT EXISTS idx_gps_points_location 
  ON gps_points USING GIST (location);

CREATE INDEX IF NOT EXISTS idx_incidents_location 
  ON incidents USING GIST (location);

-- 7. Performance B-Tree Indexes
CREATE INDEX IF NOT EXISTS idx_observations_segment_time 
  ON observations(road_segment_id, detected_at DESC);

CREATE INDEX IF NOT EXISTS idx_observations_bus 
  ON observations(bus_id);

CREATE INDEX IF NOT EXISTS idx_segment_history_segment_time 
  ON segment_history(road_segment_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_gps_points_bus_time 
  ON gps_points(bus_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_buses_status 
  ON buses(status);

-- 8. Spatial Verification Query
-- Test that PostGIS functions in the `gis` schema work properly
DO $$
BEGIN
  PERFORM gis.ST_SetSRID(gis.ST_MakePoint(76.7794, 30.7333), 4326);
  RAISE NOTICE 'PostGIS verification in gis schema successful.';
EXCEPTION WHEN OTHERS THEN
  RAISE WARNING 'PostGIS verification failed. Check if PostGIS is installed under gis schema.';
END $$;
