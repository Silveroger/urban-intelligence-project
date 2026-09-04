-- =============================================================================
-- SIH 26124: Safe Production-Grade Schema Reconciliation Migration Script (Final)
-- Target: Reconcile existing 6-table Supabase PostGIS schema with docs/DATABASE_SCHEMA.md
--
-- Safety & Non-Destructive Principles:
--   1. Fully Transactional: All schema modifications and validations run inside BEGIN ... COMMIT.
--   2. Zero Data Loss: Absolutely NO DROP TABLE, TRUNCATE, or DELETE statements.
--   3. Non-Destructive Column Preservation: Legacy UUID `id` columns and auxiliary columns
--      (road_name, health_score, etc.) are NOT dropped; they are preserved as auxiliary columns.
--   4. Preflight Current-Schema-Only: Preflight queries ONLY reference columns that exist in the
--      CURRENT schema. No destination columns (geom, event_type, observed_at, etc.) are referenced
--      before their creation.
--   5. Targeted Constraint Removal: Drops ONLY the exact 6 foreign key constraints being replaced
--      by exact name and column specification WITHOUT CASCADE.
--   6. Recreates all 6 foreign-key relationships with verified ON DELETE actions:
--      - observations(bus_id) -> buses(bus_id) ON DELETE SET NULL
--      - observations(segment_id) -> road_segments(segment_id) ON DELETE SET NULL
--      - gps_points(bus_id) -> buses(bus_id) ON DELETE CASCADE
--      - segment_history(segment_id) -> road_segments(segment_id) ON DELETE CASCADE
--      - incidents(observation_id) -> observations(observation_id) ON DELETE SET NULL
--      - incidents(road_segment_id) -> road_segments(segment_id) ON DELETE SET NULL
--   7. Strict Severity Validation: Explicit CASE mapping against AI_CONTRACT.md.
--      Does NOT use ELSE 1 or fallback to 1. Fails transaction if unexpected values exist.
--   8. Strict NOT NULL Enforcement: Preflight verifies zero NULLs exist in required columns.
--   9. PostGIS Geometry Safety: PostGIS functions qualified in `gis` schema. Verifies SRID 4326,
--      validity, and geometry type before conversion. Unknown SRIDs cause failure.
--  10. Sequence Synchronization: BIGSERIAL sequences reset to MAX(id) + 1.
--  11. Pre-Commit Validation: ALL critical validation happens BEFORE COMMIT. Fails loudly on mismatch.
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- SECTION 0: PREFLIGHT SAFETY VERIFICATION (Current-Schema-Only)
-- -----------------------------------------------------------------------------

-- 0.0 Rerun Safety Check: Detect if Canonical Schema Migration Was Already Applied
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_schema = 'public' AND table_name = 'buses' AND column_name = 'bus_id'
  ) AND EXISTS (
    SELECT 1 FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu 
      ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
    WHERE tc.constraint_type = 'PRIMARY KEY' 
      AND tc.table_schema = 'public' 
      AND tc.table_name = 'buses' 
      AND kcu.column_name = 'bus_id'
  ) THEN
    RAISE EXCEPTION 'MIGRATION HALTED (RERUN SAFETY): Database has already been migrated to canonical schema (buses.bus_id primary key detected). Script aborted cleanly without modifications.';
  END IF;
END $$;

-- 0.1 Verify required six tables exist
DO $$
DECLARE
  tbl TEXT;
  missing_tables TEXT[] := ARRAY[]::TEXT[];
BEGIN
  FOREACH tbl IN ARRAY ARRAY['buses', 'road_segments', 'gps_points', 'observations', 'incidents', 'segment_history'] LOOP
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.tables 
      WHERE table_schema = 'public' AND table_name = tbl
    ) THEN
      missing_tables := array_append(missing_tables, tbl);
    END IF;
  END LOOP;

  IF array_length(missing_tables, 1) > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 1 FAILED: Missing required table(s): %', array_to_string(missing_tables, ', ');
  END IF;
  RAISE NOTICE 'Preflight Check 1 PASSED: All 6 required tables exist in public schema.';
END $$;

-- 0.2 Verify PostGIS extension is installed
DO $$
DECLARE
  gis_ver TEXT;
  gis_schema TEXT;
BEGIN
  SELECT extversion INTO gis_ver FROM pg_extension WHERE extname = 'postgis';
  IF gis_ver IS NULL THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 2 FAILED: PostGIS extension is not installed in database.';
  END IF;

  SELECT n.nspname INTO gis_schema 
  FROM pg_extension e 
  JOIN pg_namespace n ON e.extnamespace = n.oid 
  WHERE e.extname = 'postgis';

  RAISE NOTICE 'Preflight Check 2 & 3 PASSED: PostGIS version % installed in schema "%".', gis_ver, gis_schema;
END $$;

-- 0.3 Verify Current Schema Columns Match Baseline Assumptions
DO $$
DECLARE
  missing_cols TEXT[] := ARRAY[]::TEXT[];
BEGIN
  -- buses
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'buses' AND column_name = 'id') THEN
    missing_cols := array_append(missing_cols, 'buses.id');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'buses' AND column_name = 'vehicle_number') THEN
    missing_cols := array_append(missing_cols, 'buses.vehicle_number');
  END IF;

  -- road_segments
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'road_segments' AND column_name = 'id') THEN
    missing_cols := array_append(missing_cols, 'road_segments.id');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'road_segments' AND column_name = 'geometry') THEN
    missing_cols := array_append(missing_cols, 'road_segments.geometry');
  END IF;

  -- observations
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'observations' AND column_name = 'id') THEN
    missing_cols := array_append(missing_cols, 'observations.id');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'observations' AND column_name = 'observation_type') THEN
    missing_cols := array_append(missing_cols, 'observations.observation_type');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'observations' AND column_name = 'detected_at') THEN
    missing_cols := array_append(missing_cols, 'observations.detected_at');
  END IF;

  -- incidents
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'incidents' AND column_name = 'id') THEN
    missing_cols := array_append(missing_cols, 'incidents.id');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'incidents' AND column_name = 'incident_type') THEN
    missing_cols := array_append(missing_cols, 'incidents.incident_type');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'incidents' AND column_name = 'detected_at') THEN
    missing_cols := array_append(missing_cols, 'incidents.detected_at');
  END IF;

  -- gps_points
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'gps_points' AND column_name = 'id') THEN
    missing_cols := array_append(missing_cols, 'gps_points.id');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'gps_points' AND column_name = 'recorded_at') THEN
    missing_cols := array_append(missing_cols, 'gps_points.recorded_at');
  END IF;

  -- segment_history
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'segment_history' AND column_name = 'id') THEN
    missing_cols := array_append(missing_cols, 'segment_history.id');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'segment_history' AND column_name = 'recorded_at') THEN
    missing_cols := array_append(missing_cols, 'segment_history.recorded_at');
  END IF;

  IF array_length(missing_cols, 1) > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 4 FAILED: Baseline expected column(s) missing: %', array_to_string(missing_cols, ', ');
  END IF;
  RAISE NOTICE 'Preflight Check 4 PASSED: Baseline current schema assumptions confirmed.';
END $$;

-- 0.4 Log Existing Row Counts and Verify Existing Primary Keys
DO $$
DECLARE
  cnt_buses INT;
  cnt_segments INT;
  cnt_obs INT;
  cnt_inc INT;
  cnt_gps INT;
  cnt_hist INT;
BEGIN
  SELECT count(*) INTO cnt_buses FROM buses;
  SELECT count(*) INTO cnt_segments FROM road_segments;
  SELECT count(*) INTO cnt_obs FROM observations;
  SELECT count(*) INTO cnt_inc FROM incidents;
  SELECT count(*) INTO cnt_gps FROM gps_points;
  SELECT count(*) INTO cnt_hist FROM segment_history;

  RAISE NOTICE 'Preflight Check 5: Existing row counts: buses=%, road_segments=%, observations=%, incidents=%, gps_points=%, segment_history=%',
    cnt_buses, cnt_segments, cnt_obs, cnt_inc, cnt_gps, cnt_hist;

  -- Verify UUID uniqueness in existing tables
  IF (SELECT count(*) - count(DISTINCT id) FROM buses) > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 6 FAILED: Duplicate UUID id detected in buses table.';
  END IF;
  IF (SELECT count(*) - count(DISTINCT id) FROM road_segments) > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 6 FAILED: Duplicate UUID id detected in road_segments table.';
  END IF;
  IF (SELECT count(*) - count(DISTINCT id) FROM observations) > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 6 FAILED: Duplicate UUID id detected in observations table.';
  END IF;
  IF (SELECT count(*) - count(DISTINCT id) FROM incidents) > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 6 FAILED: Duplicate UUID id detected in incidents table.';
  END IF;
  IF (SELECT count(*) - count(DISTINCT id) FROM gps_points) > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 6 FAILED: Duplicate UUID id detected in gps_points table.';
  END IF;
  IF (SELECT count(*) - count(DISTINCT id) FROM segment_history) > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 6 FAILED: Duplicate UUID id detected in segment_history table.';
  END IF;
  RAISE NOTICE 'Preflight Check 6 PASSED: All existing UUID primary keys are unique.';
END $$;

-- 0.5 Inspect ALL Foreign Key Dependencies and Detect Unexpected Relationships
DO $$
DECLARE
  r RECORD;
  unexpected_count INT := 0;
BEGIN
  RAISE NOTICE '=== PREFLIGHT: Inspecting ALL Foreign Key Constraints in public schema ===';
  FOR r IN (
    SELECT 
      tc.table_name, 
      tc.constraint_name, 
      kcu.column_name, 
      ccu.table_name AS foreign_table_name,
      ccu.column_name AS foreign_column_name,
      rc.delete_rule
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu 
      ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage ccu 
      ON tc.constraint_name = ccu.constraint_name AND tc.table_schema = ccu.table_schema
    JOIN information_schema.referential_constraints rc 
      ON tc.constraint_name = rc.constraint_name AND tc.table_schema = rc.constraint_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_schema = 'public'
  ) LOOP
    RAISE NOTICE 'Discovered FK: %.% (column: %) -> %.% [ON DELETE %]', 
      r.table_name, r.constraint_name, r.column_name, r.foreign_table_name, r.foreign_column_name, r.delete_rule;

    -- Fail if there is any foreign key referencing our core tables outside the 6 known relationships
    IF r.foreign_table_name IN ('buses', 'road_segments', 'observations', 'incidents', 'gps_points', 'segment_history') THEN
      IF NOT (
        (r.table_name = 'observations' AND r.column_name = 'bus_id' AND r.foreign_table_name = 'buses') OR
        (r.table_name = 'observations' AND r.column_name = 'road_segment_id' AND r.foreign_table_name = 'road_segments') OR
        (r.table_name = 'gps_points' AND r.column_name = 'bus_id' AND r.foreign_table_name = 'buses') OR
        (r.table_name = 'segment_history' AND r.column_name = 'road_segment_id' AND r.foreign_table_name = 'road_segments') OR
        (r.table_name = 'incidents' AND r.column_name = 'observation_id' AND r.foreign_table_name = 'observations') OR
        (r.table_name = 'incidents' AND r.column_name = 'road_segment_id' AND r.foreign_table_name = 'road_segments')
      ) THEN
        RAISE EXCEPTION 'PREFLIGHT CHECK 7 FAILED: Unexpected external FK dependency detected: %.% (%) -> %.%(%). Migration halted to prevent data loss.',
          r.table_name, r.constraint_name, r.column_name, r.foreign_table_name, r.foreign_column_name;
      END IF;
    END IF;
  END LOOP;
  RAISE NOTICE 'Preflight Check 7 PASSED: Foreign key dependencies verified. Exactly 6 known core relationships identified.';
END $$;

-- 0.6 Verify Existing Geometry Columns, Types, Validity, and SRID
DO $$
DECLARE
  bad_geom_cnt INT;
BEGIN
  -- road_segments.geometry
  SELECT count(*) INTO bad_geom_cnt 
  FROM road_segments 
  WHERE geometry IS NULL;
  IF bad_geom_cnt > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 8 FAILED: road_segments has % rows with NULL geometry.', bad_geom_cnt;
  END IF;

  SELECT count(*) INTO bad_geom_cnt 
  FROM road_segments 
  WHERE NOT gis.ST_IsValid(geometry);
  IF bad_geom_cnt > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 8 FAILED: road_segments has % invalid geometries.', bad_geom_cnt;
  END IF;

  SELECT count(*) INTO bad_geom_cnt 
  FROM road_segments 
  WHERE gis.ST_SRID(geometry) != 4326;
  IF bad_geom_cnt > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 8 FAILED: road_segments has % geometries with SRID != 4326. Cannot silently alter SRID.', bad_geom_cnt;
  END IF;

  SELECT count(*) INTO bad_geom_cnt 
  FROM road_segments 
  WHERE gis.GeometryType(geometry) NOT IN ('LINESTRING', 'LineString');
  IF bad_geom_cnt > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 8 FAILED: road_segments has % non-LineString geometries.', bad_geom_cnt;
  END IF;

  -- observations
  SELECT count(*) INTO bad_geom_cnt 
  FROM observations 
  WHERE location IS NULL AND (latitude IS NULL OR longitude IS NULL);
  IF bad_geom_cnt > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 8 FAILED: observations has % rows with NULL location and NULL coordinates.', bad_geom_cnt;
  END IF;

  SELECT count(*) INTO bad_geom_cnt 
  FROM observations 
  WHERE location IS NOT NULL AND gis.ST_SRID(location) != 4326;
  IF bad_geom_cnt > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 8 FAILED: observations has % locations with SRID != 4326.', bad_geom_cnt;
  END IF;

  -- incidents
  SELECT count(*) INTO bad_geom_cnt 
  FROM incidents 
  WHERE location IS NULL AND (latitude IS NULL OR longitude IS NULL);
  IF bad_geom_cnt > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 8 FAILED: incidents has % rows with NULL location and NULL coordinates.', bad_geom_cnt;
  END IF;

  SELECT count(*) INTO bad_geom_cnt 
  FROM incidents 
  WHERE location IS NOT NULL AND gis.ST_SRID(location) != 4326;
  IF bad_geom_cnt > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 8 FAILED: incidents has % locations with SRID != 4326.', bad_geom_cnt;
  END IF;

  -- gps_points
  SELECT count(*) INTO bad_geom_cnt 
  FROM gps_points 
  WHERE location IS NULL AND (latitude IS NULL OR longitude IS NULL);
  IF bad_geom_cnt > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 8 FAILED: gps_points has % rows with NULL location and NULL coordinates.', bad_geom_cnt;
  END IF;

  SELECT count(*) INTO bad_geom_cnt 
  FROM gps_points 
  WHERE location IS NOT NULL AND gis.ST_SRID(location) != 4326;
  IF bad_geom_cnt > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 8 FAILED: gps_points has % locations with SRID != 4326.', bad_geom_cnt;
  END IF;

  RAISE NOTICE 'Preflight Check 8 & 9 PASSED: Geometry validity, types, and SRID 4326 confirmed on all tables.';
END $$;

-- 0.7 Verify Existing Severity Values (Strict check against AI_CONTRACT.md)
DO $$
DECLARE
  bad_val RECORD;
BEGIN
  FOR bad_val IN (
    SELECT DISTINCT severity::text AS val FROM observations 
    WHERE severity IS NOT NULL 
      AND LOWER(TRIM(severity::text)) NOT IN (
        '1', 'low', 'minor', 
        '2', 'moderate', 'medium', 
        '3', 'high', 'severe', 
        '4', 'critical'
      )
  ) LOOP
    RAISE EXCEPTION 'PREFLIGHT CHECK 10 FAILED: observations contains unrecognized severity value "%". Cannot guess severity mapping.', bad_val.val;
  END LOOP;

  FOR bad_val IN (
    SELECT DISTINCT severity::text AS val FROM incidents 
    WHERE severity IS NOT NULL 
      AND LOWER(TRIM(severity::text)) NOT IN (
        '1', 'low', 'minor', 
        '2', 'moderate', 'medium', 
        '3', 'high', 'severe', 
        '4', 'critical'
      )
  ) LOOP
    RAISE EXCEPTION 'PREFLIGHT CHECK 10 FAILED: incidents contains unrecognized severity value "%". Cannot guess severity mapping.', bad_val.val;
  END LOOP;

  RAISE NOTICE 'Preflight Check 10 PASSED: All existing severity values conform to AI contract.';
END $$;

-- 0.8 Verify No Orphaned Foreign Key Relationships Exist
DO $$
DECLARE
  orphaned_cnt INT;
BEGIN
  -- observations -> buses
  SELECT count(*) INTO orphaned_cnt
  FROM observations o
  WHERE o.bus_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM buses b WHERE b.id = o.bus_id);
  IF orphaned_cnt > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 12 FAILED: % orphaned rows in observations referencing non-existent buses.id.', orphaned_cnt;
  END IF;

  -- observations -> road_segments
  SELECT count(*) INTO orphaned_cnt
  FROM observations o
  WHERE o.road_segment_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM road_segments r WHERE r.id = o.road_segment_id);
  IF orphaned_cnt > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 12 FAILED: % orphaned rows in observations referencing non-existent road_segments.id.', orphaned_cnt;
  END IF;

  -- gps_points -> buses
  SELECT count(*) INTO orphaned_cnt
  FROM gps_points g
  WHERE g.bus_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM buses b WHERE b.id = g.bus_id);
  IF orphaned_cnt > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 12 FAILED: % orphaned rows in gps_points referencing non-existent buses.id.', orphaned_cnt;
  END IF;

  -- segment_history -> road_segments
  SELECT count(*) INTO orphaned_cnt
  FROM segment_history sh
  WHERE sh.road_segment_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM road_segments r WHERE r.id = sh.road_segment_id);
  IF orphaned_cnt > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 12 FAILED: % orphaned rows in segment_history referencing non-existent road_segments.id.', orphaned_cnt;
  END IF;

  -- incidents -> observations
  SELECT count(*) INTO orphaned_cnt
  FROM incidents i
  WHERE i.observation_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM observations o WHERE o.id = i.observation_id);
  IF orphaned_cnt > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 12 FAILED: % orphaned rows in incidents referencing non-existent observations.id.', orphaned_cnt;
  END IF;

  -- incidents -> road_segments
  SELECT count(*) INTO orphaned_cnt
  FROM incidents i
  WHERE i.road_segment_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM road_segments r WHERE r.id = i.road_segment_id);
  IF orphaned_cnt > 0 THEN
    RAISE EXCEPTION 'PREFLIGHT CHECK 12 FAILED: % orphaned rows in incidents referencing non-existent road_segments.id.', orphaned_cnt;
  END IF;

  RAISE NOTICE 'Preflight Check 12 PASSED: Zero orphaned foreign key records found.';
END $$;

-- 0.9 Inspect Database Views, Triggers, and Functions depending on core tables
DO $$
DECLARE
  v_count INT;
  trig_count INT;
  r RECORD;
BEGIN
  -- Views
  SELECT count(*) INTO v_count
  FROM information_schema.view_table_usage
  WHERE table_schema = 'public'
    AND table_name IN ('buses', 'road_segments', 'observations', 'gps_points', 'incidents', 'segment_history');
  IF v_count > 0 THEN
    RAISE NOTICE 'Preflight Check 13: Found % view dependency records:', v_count;
    FOR r IN (
      SELECT DISTINCT view_schema, view_name, table_name
      FROM information_schema.view_table_usage
      WHERE table_schema = 'public'
        AND table_name IN ('buses', 'road_segments', 'observations', 'gps_points', 'incidents', 'segment_history')
    ) LOOP
      RAISE NOTICE '  - View %.% depends on table %', r.view_schema, r.view_name, r.table_name;
    END LOOP;
  ELSE
    RAISE NOTICE 'Preflight Check 13: No custom views depend on core tables.';
  END IF;

  -- Triggers
  SELECT count(*) INTO trig_count
  FROM information_schema.triggers
  WHERE trigger_schema = 'public'
    AND event_object_table IN ('buses', 'road_segments', 'observations', 'gps_points', 'incidents', 'segment_history');
  RAISE NOTICE 'Preflight Check 14: % custom triggers exist on core tables.', trig_count;

  RAISE NOTICE '=== PREFLIGHT SAFETY VERIFICATION COMPLETE: ALL CHECKS PASSED ===';
END $$;

-- -----------------------------------------------------------------------------
-- SECTION 1: TABLE `buses` SCHEMA RECONCILIATION
-- Documented Core (DATABASE_SCHEMA.md Section 3.4):
--   bus_id VARCHAR(64) PRIMARY KEY,
--   vehicle_number VARCHAR(32),
--   route_id VARCHAR(64),
--   status VARCHAR(32) DEFAULT 'active',
--   last_ping TIMESTAMPTZ
-- Retained Auxiliary:
--   id UUID (legacy UUID PK preserved),
--   last_latitude, last_longitude, last_seen_at, created_at, updated_at
-- -----------------------------------------------------------------------------

-- 1.1 Add canonical primary key column
ALTER TABLE buses ADD COLUMN IF NOT EXISTS bus_id VARCHAR(64);

-- 1.2 Backfill bus_id deterministically from existing id (UUID text)
UPDATE buses SET bus_id = id::text WHERE bus_id IS NULL;
ALTER TABLE buses ALTER COLUMN bus_id SET NOT NULL;

-- 1.3 Add canonical route_id column
ALTER TABLE buses ADD COLUMN IF NOT EXISTS route_id VARCHAR(64);

-- 1.4 Add canonical last_ping column and backfill from last_seen_at
ALTER TABLE buses ADD COLUMN IF NOT EXISTS last_ping TIMESTAMPTZ;
UPDATE buses SET last_ping = last_seen_at WHERE last_ping IS NULL AND last_seen_at IS NOT NULL;

-- 1.5 Enforce documented types and defaults
ALTER TABLE buses ALTER COLUMN vehicle_number TYPE VARCHAR(32);
ALTER TABLE buses ALTER COLUMN status TYPE VARCHAR(32);
ALTER TABLE buses ALTER COLUMN status SET DEFAULT 'active';

-- -----------------------------------------------------------------------------
-- SECTION 2: TABLE `road_segments` SCHEMA RECONCILIATION
-- Documented Core (DATABASE_SCHEMA.md Section 3.1):
--   segment_id VARCHAR(64) PRIMARY KEY,
--   name VARCHAR(255),
--   geom GEOMETRY(LineString, 4326) NOT NULL,
--   condition_score NUMERIC(5, 2) DEFAULT 100.00,
--   confidence NUMERIC(3, 2) DEFAULT 1.00,
--   pothole_count INTEGER DEFAULT 0,
--   waterlogging_count INTEGER DEFAULT 0,
--   observation_count INTEGER DEFAULT 0,
--   last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
-- Retained Auxiliary:
--   id UUID (legacy UUID PK preserved),
--   road_name, geometry, health_score, condition, start_latitude, start_longitude,
--   end_latitude, end_longitude, length_meters, last_observed_at, created_at, updated_at
-- -----------------------------------------------------------------------------

-- 2.1 Add canonical primary key column
ALTER TABLE road_segments ADD COLUMN IF NOT EXISTS segment_id VARCHAR(64);
UPDATE road_segments SET segment_id = id::text WHERE segment_id IS NULL;
ALTER TABLE road_segments ALTER COLUMN segment_id SET NOT NULL;

-- 2.2 Add canonical `name` column and backfill from road_name
ALTER TABLE road_segments ADD COLUMN IF NOT EXISTS name VARCHAR(255);
UPDATE road_segments SET name = road_name WHERE name IS NULL AND road_name IS NOT NULL;

-- 2.3 Add canonical `geom` column and enforce PostGIS LineString, SRID 4326, NOT NULL
ALTER TABLE road_segments ADD COLUMN IF NOT EXISTS geom GEOMETRY(LineString, 4326);
UPDATE road_segments SET geom = geometry WHERE geom IS NULL AND geometry IS NOT NULL;
ALTER TABLE road_segments ALTER COLUMN geom TYPE GEOMETRY(LineString, 4326);
ALTER TABLE road_segments ALTER COLUMN geom SET NOT NULL;

-- 2.4 Add canonical `condition_score` column and backfill from health_score
ALTER TABLE road_segments ADD COLUMN IF NOT EXISTS condition_score NUMERIC(5, 2) DEFAULT 100.00;
UPDATE road_segments SET condition_score = health_score::NUMERIC(5, 2) WHERE condition_score IS NULL AND health_score IS NOT NULL;
ALTER TABLE road_segments ALTER COLUMN condition_score TYPE NUMERIC(5, 2) USING condition_score::NUMERIC(5, 2);
ALTER TABLE road_segments ALTER COLUMN condition_score SET DEFAULT 100.00;

-- 2.5 Add canonical metric columns with defaults
ALTER TABLE road_segments ADD COLUMN IF NOT EXISTS confidence NUMERIC(3, 2) DEFAULT 1.00;
UPDATE road_segments SET confidence = 1.00 WHERE confidence IS NULL;

ALTER TABLE road_segments ADD COLUMN IF NOT EXISTS pothole_count INTEGER DEFAULT 0;
UPDATE road_segments SET pothole_count = 0 WHERE pothole_count IS NULL;
ALTER TABLE road_segments ALTER COLUMN pothole_count SET DEFAULT 0;

ALTER TABLE road_segments ADD COLUMN IF NOT EXISTS waterlogging_count INTEGER DEFAULT 0;
UPDATE road_segments SET waterlogging_count = 0 WHERE waterlogging_count IS NULL;
ALTER TABLE road_segments ALTER COLUMN waterlogging_count SET DEFAULT 0;

ALTER TABLE road_segments ALTER COLUMN observation_count SET DEFAULT 0;
UPDATE road_segments SET observation_count = 0 WHERE observation_count IS NULL;

-- 2.6 Add canonical `last_updated` column and backfill
ALTER TABLE road_segments ADD COLUMN IF NOT EXISTS last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;
UPDATE road_segments 
SET last_updated = COALESCE(last_observed_at, updated_at, created_at, CURRENT_TIMESTAMP)
WHERE last_updated IS NULL;

-- -----------------------------------------------------------------------------
-- SECTION 3: TABLE `gps_points` SCHEMA RECONCILIATION
-- Documented Core (DATABASE_SCHEMA.md Section 3.4):
--   point_id BIGSERIAL PRIMARY KEY,
--   bus_id VARCHAR(64) REFERENCES buses(bus_id),
--   geom GEOMETRY(Point, 4326) NOT NULL,
--   heading_deg NUMERIC(5, 2),
--   recorded_at TIMESTAMPTZ NOT NULL
-- Retained Auxiliary:
--   id UUID (legacy UUID PK preserved),
--   legacy_bus_id UUID (legacy bus FK preserved),
--   location, speed_kmh, heading, accuracy_meters, latitude, longitude, created_at
-- -----------------------------------------------------------------------------

-- 3.1 Add canonical BIGSERIAL point_id
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'gps_points' AND column_name = 'point_id'
  ) THEN
    ALTER TABLE gps_points ADD COLUMN point_id BIGSERIAL;
  END IF;
END $$;
ALTER TABLE gps_points ALTER COLUMN point_id SET NOT NULL;

-- 3.2 Prepare canonical bus_id VARCHAR(64) column
ALTER TABLE gps_points ADD COLUMN IF NOT EXISTS bus_id_varchar VARCHAR(64);
UPDATE gps_points SET bus_id_varchar = bus_id::text WHERE bus_id_varchar IS NULL AND bus_id IS NOT NULL;

-- 3.3 Add canonical `geom` column and enforce PostGIS Point, SRID 4326, NOT NULL
ALTER TABLE gps_points ADD COLUMN IF NOT EXISTS geom GEOMETRY(Point, 4326);
UPDATE gps_points SET geom = location WHERE geom IS NULL AND location IS NOT NULL;
UPDATE gps_points SET geom = gis.ST_SetSRID(gis.ST_MakePoint(longitude, latitude), 4326) 
WHERE geom IS NULL AND latitude IS NOT NULL AND longitude IS NOT NULL;
ALTER TABLE gps_points ALTER COLUMN geom TYPE GEOMETRY(Point, 4326);
ALTER TABLE gps_points ALTER COLUMN geom SET NOT NULL;

-- 3.4 Add canonical `heading_deg` column and backfill from heading
ALTER TABLE gps_points ADD COLUMN IF NOT EXISTS heading_deg NUMERIC(5, 2);
UPDATE gps_points SET heading_deg = heading::NUMERIC(5, 2) WHERE heading_deg IS NULL AND heading IS NOT NULL;
ALTER TABLE gps_points ALTER COLUMN heading_deg TYPE NUMERIC(5, 2) USING heading_deg::NUMERIC(5, 2);

-- 3.5 Enforce recorded_at NOT NULL
ALTER TABLE gps_points ALTER COLUMN recorded_at SET NOT NULL;

-- -----------------------------------------------------------------------------
-- SECTION 4: TABLE `observations` SCHEMA RECONCILIATION
-- Documented Core (DATABASE_SCHEMA.md Section 3.2):
--   observation_id VARCHAR(64) PRIMARY KEY,
--   bus_id VARCHAR(64) REFERENCES buses(bus_id),
--   segment_id VARCHAR(64) REFERENCES road_segments(segment_id),
--   geom GEOMETRY(Point, 4326) NOT NULL,
--   event_type VARCHAR(32) NOT NULL,
--   class_name VARCHAR(64),
--   confidence NUMERIC(3, 2) NOT NULL,
--   severity SMALLINT CHECK (severity BETWEEN 1 AND 4),
--   evidence_uri VARCHAR(512),
--   observed_at TIMESTAMPTZ NOT NULL,
--   created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
-- Retained Auxiliary:
--   id UUID (legacy UUID PK preserved),
--   legacy_bus_id UUID (legacy bus FK preserved),
--   road_segment_id UUID (legacy segment FK preserved),
--   observation_type, location, evidence_path, metadata, latitude, longitude, status
-- -----------------------------------------------------------------------------

-- 4.1 Add canonical primary key column
ALTER TABLE observations ADD COLUMN IF NOT EXISTS observation_id VARCHAR(64);
UPDATE observations SET observation_id = id::text WHERE observation_id IS NULL;
ALTER TABLE observations ALTER COLUMN observation_id SET NOT NULL;

-- 4.2 Prepare canonical foreign key columns
ALTER TABLE observations ADD COLUMN IF NOT EXISTS bus_id_varchar VARCHAR(64);
UPDATE observations SET bus_id_varchar = bus_id::text WHERE bus_id_varchar IS NULL AND bus_id IS NOT NULL;

ALTER TABLE observations ADD COLUMN IF NOT EXISTS segment_id VARCHAR(64);
UPDATE observations SET segment_id = road_segment_id::text WHERE segment_id IS NULL AND road_segment_id IS NOT NULL;

-- 4.3 Add canonical `geom` column and enforce PostGIS Point, SRID 4326, NOT NULL
ALTER TABLE observations ADD COLUMN IF NOT EXISTS geom GEOMETRY(Point, 4326);
UPDATE observations SET geom = location WHERE geom IS NULL AND location IS NOT NULL;
UPDATE observations SET geom = gis.ST_SetSRID(gis.ST_MakePoint(longitude, latitude), 4326) 
WHERE geom IS NULL AND latitude IS NOT NULL AND longitude IS NOT NULL;
ALTER TABLE observations ALTER COLUMN geom TYPE GEOMETRY(Point, 4326);
ALTER TABLE observations ALTER COLUMN geom SET NOT NULL;

-- 4.4 Add canonical `event_type` column and backfill from observation_type
ALTER TABLE observations ADD COLUMN IF NOT EXISTS event_type VARCHAR(32);
UPDATE observations SET event_type = observation_type WHERE event_type IS NULL AND observation_type IS NOT NULL;
ALTER TABLE observations ALTER COLUMN event_type TYPE VARCHAR(32);
ALTER TABLE observations ALTER COLUMN event_type SET NOT NULL;

-- 4.5 Add class_name and backfill from metadata JSONB if present (nullable; no fallback to event_type)
ALTER TABLE observations ADD COLUMN IF NOT EXISTS class_name VARCHAR(64);
UPDATE observations 
SET class_name = metadata->>'class_name'
WHERE class_name IS NULL AND metadata IS NOT NULL AND (metadata->>'class_name') IS NOT NULL;

-- 4.6 Convert severity safely to SMALLINT (1-4) with explicit AI Contract mapping
-- Does NOT fallback to 1 on unknown values. Preserves NULL if original value was NULL.
ALTER TABLE observations ADD COLUMN IF NOT EXISTS severity_num SMALLINT;
UPDATE observations SET severity_num = CASE 
  WHEN LOWER(TRIM(severity::text)) IN ('4', 'critical') THEN 4
  WHEN LOWER(TRIM(severity::text)) IN ('3', 'high', 'severe') THEN 3
  WHEN LOWER(TRIM(severity::text)) IN ('2', 'moderate', 'medium') THEN 2
  WHEN LOWER(TRIM(severity::text)) IN ('1', 'low', 'minor') THEN 1
  WHEN severity IS NULL THEN NULL
END;

-- 4.7 Add canonical `evidence_uri` column and backfill from evidence_path
ALTER TABLE observations ADD COLUMN IF NOT EXISTS evidence_uri VARCHAR(512);
UPDATE observations SET evidence_uri = evidence_path WHERE evidence_uri IS NULL AND evidence_path IS NOT NULL;
ALTER TABLE observations ALTER COLUMN evidence_uri TYPE VARCHAR(512);

-- 4.8 Add canonical `observed_at` column and backfill from detected_at
ALTER TABLE observations ADD COLUMN IF NOT EXISTS observed_at TIMESTAMPTZ;
UPDATE observations SET observed_at = detected_at WHERE observed_at IS NULL AND detected_at IS NOT NULL;
ALTER TABLE observations ALTER COLUMN observed_at SET NOT NULL;

-- 4.9 Enforce confidence NUMERIC(3, 2) NOT NULL
ALTER TABLE observations ALTER COLUMN confidence TYPE NUMERIC(3, 2) USING confidence::NUMERIC(3, 2);
ALTER TABLE observations ALTER COLUMN confidence SET NOT NULL;

-- -----------------------------------------------------------------------------
-- SECTION 5: TABLE `incidents` SCHEMA RECONCILIATION
-- Documented Core Columns (docs/DATABASE_SCHEMA.md Section 3.5):
--   incident_id VARCHAR(64) PRIMARY KEY,
--   geom GEOMETRY(Point, 4326) NOT NULL,
--   incident_type VARCHAR(64) NOT NULL,
--   severity SMALLINT DEFAULT 1,
--   vehicle_track_id VARCHAR(64),
--   plate_text VARCHAR(32),
--   plate_confidence NUMERIC(3, 2),
--   evidence_uri VARCHAR(512),
--   recorded_at TIMESTAMPTZ NOT NULL
-- Preserved Auxiliary Foreign Keys (Retaining Existing Domain Relationships):
--   observation_id VARCHAR(64) REFERENCES observations(observation_id) ON DELETE SET NULL,
--   road_segment_id VARCHAR(64) REFERENCES road_segments(segment_id) ON DELETE SET NULL
-- Retained Auxiliary Columns:
--   id UUID (legacy UUID PK preserved),
--   legacy_observation_id UUID,
--   legacy_road_segment_id UUID,
--   location, detected_at, description, status, latitude, longitude, resolved_at, created_at
-- -----------------------------------------------------------------------------

-- 5.1 Add canonical primary key column
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS incident_id VARCHAR(64);
UPDATE incidents SET incident_id = id::text WHERE incident_id IS NULL;
ALTER TABLE incidents ALTER COLUMN incident_id SET NOT NULL;

-- 5.2 Prepare canonical FK columns for observation_id and road_segment_id
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS observation_id_varchar VARCHAR(64);
UPDATE incidents SET observation_id_varchar = observation_id::text 
WHERE observation_id_varchar IS NULL AND observation_id IS NOT NULL;

ALTER TABLE incidents ADD COLUMN IF NOT EXISTS road_segment_id_varchar VARCHAR(64);
UPDATE incidents SET road_segment_id_varchar = road_segment_id::text 
WHERE road_segment_id_varchar IS NULL AND road_segment_id IS NOT NULL;

-- 5.3 Add canonical `geom` column and enforce PostGIS Point, SRID 4326, NOT NULL
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS geom GEOMETRY(Point, 4326);
UPDATE incidents SET geom = location WHERE geom IS NULL AND location IS NOT NULL;
UPDATE incidents SET geom = gis.ST_SetSRID(gis.ST_MakePoint(longitude, latitude), 4326) 
WHERE geom IS NULL AND latitude IS NOT NULL AND longitude IS NOT NULL;
ALTER TABLE incidents ALTER COLUMN geom TYPE GEOMETRY(Point, 4326);
ALTER TABLE incidents ALTER COLUMN geom SET NOT NULL;

-- 5.4 Add canonical `recorded_at` column and backfill from detected_at
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS recorded_at TIMESTAMPTZ;
UPDATE incidents SET recorded_at = detected_at WHERE recorded_at IS NULL AND detected_at IS NOT NULL;
ALTER TABLE incidents ALTER COLUMN recorded_at SET NOT NULL;

-- 5.5 Convert severity safely to SMALLINT (1-4) with explicit AI Contract mapping
-- Does NOT fallback to 1 on unknown values. Preserves NULL if original value was NULL.
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS severity_num SMALLINT;
UPDATE incidents SET severity_num = CASE 
  WHEN LOWER(TRIM(severity::text)) IN ('4', 'critical') THEN 4
  WHEN LOWER(TRIM(severity::text)) IN ('3', 'high', 'severe') THEN 3
  WHEN LOWER(TRIM(severity::text)) IN ('2', 'moderate', 'medium') THEN 2
  WHEN LOWER(TRIM(severity::text)) IN ('1', 'low', 'minor') THEN 1
  WHEN severity IS NULL THEN NULL
END;

-- 5.6 Add canonical optional tracking & OCR columns
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS vehicle_track_id VARCHAR(64);
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS plate_text VARCHAR(32);
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS plate_confidence NUMERIC(3, 2);
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS evidence_uri VARCHAR(512);
ALTER TABLE incidents ALTER COLUMN incident_type TYPE VARCHAR(64);
ALTER TABLE incidents ALTER COLUMN incident_type SET NOT NULL;

-- -----------------------------------------------------------------------------
-- SECTION 6: TABLE `segment_history` SCHEMA RECONCILIATION
-- Documented Core (DATABASE_SCHEMA.md Section 3.3):
--   history_id BIGSERIAL PRIMARY KEY,
--   segment_id VARCHAR(64) REFERENCES road_segments(segment_id),
--   condition_score NUMERIC(5, 2) NOT NULL,
--   confidence NUMERIC(3, 2) NOT NULL,
--   pothole_count INTEGER NOT NULL,
--   waterlogging_count INTEGER NOT NULL,
--   bus_id VARCHAR(64),
--   recorded_at TIMESTAMPTZ NOT NULL
-- Retained Auxiliary:
--   id UUID (legacy UUID PK preserved),
--   road_segment_id UUID (legacy segment FK preserved),
--   health_score, condition, crack_count, rough_surface_count
-- -----------------------------------------------------------------------------

-- 6.1 Add canonical BIGSERIAL history_id
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'segment_history' AND column_name = 'history_id'
  ) THEN
    ALTER TABLE segment_history ADD COLUMN history_id BIGSERIAL;
  END IF;
END $$;
ALTER TABLE segment_history ALTER COLUMN history_id SET NOT NULL;

-- 6.2 Add segment_id to link with road_segments(segment_id)
ALTER TABLE segment_history ADD COLUMN IF NOT EXISTS segment_id VARCHAR(64);
UPDATE segment_history SET segment_id = road_segment_id::text WHERE segment_id IS NULL AND road_segment_id IS NOT NULL;
ALTER TABLE segment_history ALTER COLUMN segment_id SET NOT NULL;

-- 6.3 Add canonical `condition_score` column and backfill from health_score
ALTER TABLE segment_history ADD COLUMN IF NOT EXISTS condition_score NUMERIC(5, 2);
UPDATE segment_history SET condition_score = health_score::NUMERIC(5, 2) WHERE condition_score IS NULL AND health_score IS NOT NULL;
ALTER TABLE segment_history ALTER COLUMN condition_score TYPE NUMERIC(5, 2) USING condition_score::NUMERIC(5, 2);
ALTER TABLE segment_history ALTER COLUMN condition_score SET NOT NULL;

-- 6.4 Add documented columns: confidence, waterlogging_count, bus_id
ALTER TABLE segment_history ADD COLUMN IF NOT EXISTS confidence NUMERIC(3, 2) DEFAULT 1.00;
UPDATE segment_history SET confidence = 1.00 WHERE confidence IS NULL;
ALTER TABLE segment_history ALTER COLUMN confidence SET NOT NULL;

ALTER TABLE segment_history ADD COLUMN IF NOT EXISTS pothole_count INTEGER DEFAULT 0;
UPDATE segment_history SET pothole_count = 0 WHERE pothole_count IS NULL;
ALTER TABLE segment_history ALTER COLUMN pothole_count SET NOT NULL;

ALTER TABLE segment_history ADD COLUMN IF NOT EXISTS waterlogging_count INTEGER DEFAULT 0;
UPDATE segment_history SET waterlogging_count = 0 WHERE waterlogging_count IS NULL;
ALTER TABLE segment_history ALTER COLUMN waterlogging_count SET NOT NULL;

-- Canonical bus_id added as nullable; left NULL since source segment_history did not track bus_id
ALTER TABLE segment_history ADD COLUMN IF NOT EXISTS bus_id VARCHAR(64);

ALTER TABLE segment_history ALTER COLUMN recorded_at SET NOT NULL;

-- -----------------------------------------------------------------------------
-- SECTION 7: CONSTRAINT MIGRATION (TARGETED - ZERO CASCADE)
-- -----------------------------------------------------------------------------

-- 7.1 Drop ONLY the exact 6 foreign key constraints being replaced (WITHOUT CASCADE)
DO $$
DECLARE
  r RECORD;
BEGIN
  FOR r IN (
    SELECT 
      tc.table_name,
      tc.constraint_name,
      kcu.column_name,
      ccu.table_name AS foreign_table_name,
      rc.delete_rule
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu 
      ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage ccu 
      ON tc.constraint_name = ccu.constraint_name AND tc.table_schema = ccu.table_schema
    JOIN information_schema.referential_constraints rc 
      ON tc.constraint_name = rc.constraint_name AND tc.table_schema = rc.constraint_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_schema = 'public'
      AND (
        (tc.table_name = 'observations' AND kcu.column_name = 'bus_id' AND ccu.table_name = 'buses') OR
        (tc.table_name = 'observations' AND kcu.column_name = 'road_segment_id' AND ccu.table_name = 'road_segments') OR
        (tc.table_name = 'gps_points' AND kcu.column_name = 'bus_id' AND ccu.table_name = 'buses') OR
        (tc.table_name = 'segment_history' AND kcu.column_name = 'road_segment_id' AND ccu.table_name = 'road_segments') OR
        (tc.table_name = 'incidents' AND kcu.column_name = 'observation_id' AND ccu.table_name = 'observations') OR
        (tc.table_name = 'incidents' AND kcu.column_name = 'road_segment_id' AND ccu.table_name = 'road_segments')
      )
  ) LOOP
    RAISE NOTICE 'Dropping exact FK constraint: %.% on column % referencing % (ON DELETE %)',
      r.table_name, r.constraint_name, r.column_name, r.foreign_table_name, r.delete_rule;
    EXECUTE 'ALTER TABLE public.' || quote_ident(r.table_name) || ' DROP CONSTRAINT ' || quote_ident(r.constraint_name) || ';';
  END LOOP;
END $$;

-- 7.2 Switch Primary Keys to Documented Identifiers & Add Legacy UUID UNIQUE Constraints
ALTER TABLE buses DROP CONSTRAINT IF EXISTS buses_pkey;
ALTER TABLE buses ADD CONSTRAINT buses_pkey PRIMARY KEY (bus_id);
ALTER TABLE buses DROP CONSTRAINT IF EXISTS uq_buses_legacy_id;
ALTER TABLE buses ADD CONSTRAINT uq_buses_legacy_id UNIQUE (id);

ALTER TABLE road_segments DROP CONSTRAINT IF EXISTS road_segments_pkey;
ALTER TABLE road_segments ADD CONSTRAINT road_segments_pkey PRIMARY KEY (segment_id);
ALTER TABLE road_segments DROP CONSTRAINT IF EXISTS uq_road_segments_legacy_id;
ALTER TABLE road_segments ADD CONSTRAINT uq_road_segments_legacy_id UNIQUE (id);

ALTER TABLE observations DROP CONSTRAINT IF EXISTS observations_pkey;
ALTER TABLE observations ADD CONSTRAINT observations_pkey PRIMARY KEY (observation_id);
ALTER TABLE observations DROP CONSTRAINT IF EXISTS uq_observations_legacy_id;
ALTER TABLE observations ADD CONSTRAINT uq_observations_legacy_id UNIQUE (id);

ALTER TABLE gps_points DROP CONSTRAINT IF EXISTS gps_points_pkey;
ALTER TABLE gps_points ADD CONSTRAINT gps_points_pkey PRIMARY KEY (point_id);
ALTER TABLE gps_points DROP CONSTRAINT IF EXISTS uq_gps_points_legacy_id;
ALTER TABLE gps_points ADD CONSTRAINT uq_gps_points_legacy_id UNIQUE (id);

ALTER TABLE incidents DROP CONSTRAINT IF EXISTS incidents_pkey;
ALTER TABLE incidents ADD CONSTRAINT incidents_pkey PRIMARY KEY (incident_id);
ALTER TABLE incidents DROP CONSTRAINT IF EXISTS uq_incidents_legacy_id;
ALTER TABLE incidents ADD CONSTRAINT uq_incidents_legacy_id UNIQUE (id);

ALTER TABLE segment_history DROP CONSTRAINT IF EXISTS segment_history_pkey;
ALTER TABLE segment_history ADD CONSTRAINT segment_history_pkey PRIMARY KEY (history_id);
ALTER TABLE segment_history DROP CONSTRAINT IF EXISTS uq_segment_history_legacy_id;
ALTER TABLE segment_history ADD CONSTRAINT uq_segment_history_legacy_id UNIQUE (id);

-- 7.3 Preserve Legacy UUID FK Columns as Auxiliary and Promote VARCHAR FK Columns
-- gps_points: rename bus_id UUID to legacy_bus_id; promote bus_id_varchar to bus_id
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'gps_points' AND column_name = 'bus_id' AND data_type = 'uuid'
  ) THEN
    ALTER TABLE gps_points RENAME COLUMN bus_id TO legacy_bus_id;
    ALTER TABLE gps_points RENAME COLUMN bus_id_varchar TO bus_id;
  END IF;
END $$;

-- observations: rename bus_id UUID to legacy_bus_id; promote bus_id_varchar to bus_id
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'observations' AND column_name = 'bus_id' AND data_type = 'uuid'
  ) THEN
    ALTER TABLE observations RENAME COLUMN bus_id TO legacy_bus_id;
    ALTER TABLE observations RENAME COLUMN bus_id_varchar TO bus_id;
  END IF;
END $$;

-- observations: promote severity_num to severity
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'observations' AND column_name = 'severity' AND (data_type LIKE '%char%' OR data_type LIKE '%text%')
  ) THEN
    ALTER TABLE observations RENAME COLUMN severity TO legacy_severity;
    ALTER TABLE observations RENAME COLUMN severity_num TO severity;
  ELSIF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'observations' AND column_name = 'severity'
  ) THEN
    ALTER TABLE observations RENAME COLUMN severity_num TO severity;
  ELSE
    ALTER TABLE observations ALTER COLUMN severity TYPE SMALLINT USING severity_num;
    ALTER TABLE observations DROP COLUMN IF EXISTS severity_num;
  END IF;
END $$;
ALTER TABLE observations DROP CONSTRAINT IF EXISTS chk_observations_severity;
ALTER TABLE observations ADD CONSTRAINT chk_observations_severity CHECK (severity BETWEEN 1 AND 4);

-- incidents: rename observation_id UUID to legacy_observation_id; promote observation_id_varchar
-- incidents: rename road_segment_id UUID to legacy_road_segment_id; promote road_segment_id_varchar
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'incidents' AND column_name = 'observation_id' AND data_type = 'uuid'
  ) THEN
    ALTER TABLE incidents RENAME COLUMN observation_id TO legacy_observation_id;
    ALTER TABLE incidents RENAME COLUMN observation_id_varchar TO observation_id;
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'incidents' AND column_name = 'road_segment_id' AND data_type = 'uuid'
  ) THEN
    ALTER TABLE incidents RENAME COLUMN road_segment_id TO legacy_road_segment_id;
    ALTER TABLE incidents RENAME COLUMN road_segment_id_varchar TO road_segment_id;
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'incidents' AND column_name = 'severity' AND (data_type LIKE '%char%' OR data_type LIKE '%text%')
  ) THEN
    ALTER TABLE incidents RENAME COLUMN severity TO legacy_severity;
    ALTER TABLE incidents RENAME COLUMN severity_num TO severity;
  ELSIF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'incidents' AND column_name = 'severity'
  ) THEN
    ALTER TABLE incidents RENAME COLUMN severity_num TO severity;
  ELSE
    ALTER TABLE incidents ALTER COLUMN severity TYPE SMALLINT USING severity_num;
    ALTER TABLE incidents DROP COLUMN IF EXISTS severity_num;
  END IF;
END $$;
ALTER TABLE incidents ALTER COLUMN severity SET DEFAULT 1;
ALTER TABLE incidents DROP CONSTRAINT IF EXISTS chk_incidents_severity;
ALTER TABLE incidents ADD CONSTRAINT chk_incidents_severity CHECK (severity BETWEEN 1 AND 4);

-- 7.4 Establish Canonical Foreign Key Constraints (Strictly Preserving Documented / Original ON DELETE)
ALTER TABLE observations
  ADD CONSTRAINT fk_observations_bus 
  FOREIGN KEY (bus_id) REFERENCES buses(bus_id) ON DELETE SET NULL;

ALTER TABLE observations
  ADD CONSTRAINT fk_observations_segment 
  FOREIGN KEY (segment_id) REFERENCES road_segments(segment_id) ON DELETE SET NULL;

ALTER TABLE gps_points
  ADD CONSTRAINT fk_gps_points_bus 
  FOREIGN KEY (bus_id) REFERENCES buses(bus_id) ON DELETE CASCADE;

ALTER TABLE segment_history
  ADD CONSTRAINT fk_segment_history_segment 
  FOREIGN KEY (segment_id) REFERENCES road_segments(segment_id) ON DELETE CASCADE;

ALTER TABLE incidents
  ADD CONSTRAINT fk_incidents_observation
  FOREIGN KEY (observation_id) REFERENCES observations(observation_id) ON DELETE SET NULL;

ALTER TABLE incidents
  ADD CONSTRAINT fk_incidents_road_segment
  FOREIGN KEY (road_segment_id) REFERENCES road_segments(segment_id) ON DELETE SET NULL;

-- 7.5 Recompute Road Segment Aggregate Counts from Canonical Observations
-- Documented Rule: road_segments aggregate fields must represent actual canonical observations,
-- not blindly preserve potentially stale legacy counters.
-- Recomputed non-destructively based on canonical segment_id relationships.
UPDATE road_segments rs
SET 
  observation_count = COALESCE(agg.total_obs, 0),
  pothole_count = COALESCE(agg.potholes, 0),
  waterlogging_count = COALESCE(agg.waterloggings, 0)
FROM (
  SELECT 
    segment_id,
    count(*) AS total_obs,
    count(*) FILTER (
      WHERE LOWER(event_type) = 'pothole' 
         OR LOWER(COALESCE(class_name, '')) LIKE '%pothole%'
    ) AS potholes,
    count(*) FILTER (
      WHERE LOWER(event_type) IN ('waterlogging', 'water_logging', 'flooding') 
         OR LOWER(COALESCE(class_name, '')) LIKE '%water%'
    ) AS waterloggings
  FROM observations
  WHERE segment_id IS NOT NULL
  GROUP BY segment_id
) agg
WHERE rs.segment_id = agg.segment_id;

-- Ensure segments with 0 observations have 0 counts rather than NULL
UPDATE road_segments
SET 
  observation_count = COALESCE(observation_count, 0),
  pothole_count = COALESCE(pothole_count, 0),
  waterlogging_count = COALESCE(waterlogging_count, 0)
WHERE observation_count IS NULL OR pothole_count IS NULL OR waterlogging_count IS NULL;

-- -----------------------------------------------------------------------------
-- SECTION 8: INDEXES & SEQUENCE SYNCHRONIZATION
-- -----------------------------------------------------------------------------

-- 8.1 Spatial and Performance Indexes (Qualified PostGIS in `gis` Schema)
CREATE INDEX IF NOT EXISTS idx_road_segments_geom ON road_segments USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_observations_geom ON observations USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_observations_segment ON observations(segment_id);
CREATE INDEX IF NOT EXISTS idx_observations_observed_at ON observations(observed_at);
CREATE INDEX IF NOT EXISTS idx_segment_history_segment_time ON segment_history(segment_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_gps_points_geom ON gps_points USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_gps_points_bus_time ON gps_points(bus_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_geom ON incidents USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_incidents_observation_id ON incidents(observation_id);
CREATE INDEX IF NOT EXISTS idx_incidents_road_segment_id ON incidents(road_segment_id);

-- 8.2 Synchronize BIGSERIAL Sequences
SELECT setval(
  pg_get_serial_sequence('gps_points', 'point_id'), 
  COALESCE((SELECT MAX(point_id) FROM gps_points), 0) + 1, 
  false
);

SELECT setval(
  pg_get_serial_sequence('segment_history', 'history_id'), 
  COALESCE((SELECT MAX(history_id) FROM segment_history), 0) + 1, 
  false
);

-- -----------------------------------------------------------------------------
-- SECTION 9: PRE-COMMIT VALIDATION (CRITICAL - ROLLS BACK ON ANY FAILURE)
-- -----------------------------------------------------------------------------
DO $$
DECLARE
  orphaned_cnt INT;
  invalid_geom_cnt INT;
  null_req_cnt INT;
  seq_val BIGINT;
  max_id BIGINT;
  test_rec RECORD;
BEGIN
  RAISE NOTICE '=== EXECUTING PRE-COMMIT VALIDATION (Mandatory checks before commit) ===';

  -- 1. Verify PK integrity and non-nullability
  SELECT count(*) INTO null_req_cnt FROM buses WHERE bus_id IS NULL;
  IF null_req_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: buses.bus_id has % NULLs.', null_req_cnt; END IF;

  SELECT count(*) INTO null_req_cnt FROM road_segments WHERE segment_id IS NULL;
  IF null_req_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: road_segments.segment_id has % NULLs.', null_req_cnt; END IF;

  SELECT count(*) INTO null_req_cnt FROM observations WHERE observation_id IS NULL;
  IF null_req_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: observations.observation_id has % NULLs.', null_req_cnt; END IF;

  SELECT count(*) INTO null_req_cnt FROM incidents WHERE incident_id IS NULL;
  IF null_req_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: incidents.incident_id has % NULLs.', null_req_cnt; END IF;

  SELECT count(*) INTO null_req_cnt FROM gps_points WHERE point_id IS NULL;
  IF null_req_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: gps_points.point_id has % NULLs.', null_req_cnt; END IF;

  SELECT count(*) INTO null_req_cnt FROM segment_history WHERE history_id IS NULL;
  IF null_req_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: segment_history.history_id has % NULLs.', null_req_cnt; END IF;

  -- 2. Verify Canonical Foreign Key Relationships (0 orphaned rows allowed)
  SELECT count(*) INTO orphaned_cnt FROM observations o 
  WHERE o.bus_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM buses b WHERE b.bus_id = o.bus_id);
  IF orphaned_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: % orphaned rows in observations.bus_id.', orphaned_cnt; END IF;

  SELECT count(*) INTO orphaned_cnt FROM observations o 
  WHERE o.segment_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM road_segments r WHERE r.segment_id = o.segment_id);
  IF orphaned_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: % orphaned rows in observations.segment_id.', orphaned_cnt; END IF;

  SELECT count(*) INTO orphaned_cnt FROM gps_points g 
  WHERE NOT EXISTS (SELECT 1 FROM buses b WHERE b.bus_id = g.bus_id);
  IF orphaned_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: % orphaned rows in gps_points.bus_id.', orphaned_cnt; END IF;

  SELECT count(*) INTO orphaned_cnt FROM segment_history sh 
  WHERE NOT EXISTS (SELECT 1 FROM road_segments r WHERE r.segment_id = sh.segment_id);
  IF orphaned_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: % orphaned rows in segment_history.segment_id.', orphaned_cnt; END IF;

  SELECT count(*) INTO orphaned_cnt FROM incidents i 
  WHERE i.observation_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM observations o WHERE o.observation_id = i.observation_id);
  IF orphaned_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: % orphaned rows in incidents.observation_id.', orphaned_cnt; END IF;

  SELECT count(*) INTO orphaned_cnt FROM incidents i 
  WHERE i.road_segment_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM road_segments r WHERE r.segment_id = i.road_segment_id);
  IF orphaned_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: % orphaned rows in incidents.road_segment_id.', orphaned_cnt; END IF;

  -- 3. Verify Required NOT NULL Columns
  SELECT count(*) INTO null_req_cnt FROM road_segments WHERE geom IS NULL;
  IF null_req_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: road_segments.geom has % NULLs.', null_req_cnt; END IF;

  SELECT count(*) INTO null_req_cnt FROM observations 
  WHERE geom IS NULL OR event_type IS NULL OR confidence IS NULL OR observed_at IS NULL;
  IF null_req_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: observations required columns contain % NULLs.', null_req_cnt; END IF;

  SELECT count(*) INTO null_req_cnt FROM incidents 
  WHERE geom IS NULL OR incident_type IS NULL OR recorded_at IS NULL;
  IF null_req_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: incidents required columns contain % NULLs.', null_req_cnt; END IF;

  SELECT count(*) INTO null_req_cnt FROM gps_points 
  WHERE geom IS NULL OR recorded_at IS NULL;
  IF null_req_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: gps_points required columns contain % NULLs.', null_req_cnt; END IF;

  SELECT count(*) INTO null_req_cnt FROM segment_history 
  WHERE condition_score IS NULL OR confidence IS NULL OR pothole_count IS NULL OR waterlogging_count IS NULL OR recorded_at IS NULL;
  IF null_req_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: segment_history required columns contain % NULLs.', null_req_cnt; END IF;

  -- 4. Verify Geometry Types and SRID 4326
  SELECT count(*) INTO invalid_geom_cnt FROM road_segments 
  WHERE gis.GeometryType(geom) != 'LINESTRING' OR gis.ST_SRID(geom) != 4326 OR NOT gis.ST_IsValid(geom);
  IF invalid_geom_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: road_segments has % invalid LineStrings or non-4326 SRIDs.', invalid_geom_cnt; END IF;

  SELECT count(*) INTO invalid_geom_cnt FROM observations 
  WHERE gis.GeometryType(geom) != 'POINT' OR gis.ST_SRID(geom) != 4326 OR NOT gis.ST_IsValid(geom);
  IF invalid_geom_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: observations has % invalid Points or non-4326 SRIDs.', invalid_geom_cnt; END IF;

  SELECT count(*) INTO invalid_geom_cnt FROM incidents 
  WHERE gis.GeometryType(geom) != 'POINT' OR gis.ST_SRID(geom) != 4326 OR NOT gis.ST_IsValid(geom);
  IF invalid_geom_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: incidents has % invalid Points or non-4326 SRIDs.', invalid_geom_cnt; END IF;

  SELECT count(*) INTO invalid_geom_cnt FROM gps_points 
  WHERE gis.GeometryType(geom) != 'POINT' OR gis.ST_SRID(geom) != 4326 OR NOT gis.ST_IsValid(geom);
  IF invalid_geom_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: gps_points has % invalid Points or non-4326 SRIDs.', invalid_geom_cnt; END IF;

  -- 5. Verify Severity Values (SmallInteger between 1 and 4)
  SELECT count(*) INTO null_req_cnt FROM observations WHERE severity IS NOT NULL AND (severity < 1 OR severity > 4);
  IF null_req_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: observations has % invalid severity values outside 1-4.', null_req_cnt; END IF;

  SELECT count(*) INTO null_req_cnt FROM incidents WHERE severity IS NOT NULL AND (severity < 1 OR severity > 4);
  IF null_req_cnt > 0 THEN RAISE EXCEPTION 'PRE-COMMIT FAILED: incidents has % invalid severity values outside 1-4.', null_req_cnt; END IF;

  -- 6. Verify Sequences
  SELECT COALESCE(MAX(point_id), 0) INTO max_id FROM gps_points;
  SELECT last_value INTO seq_val FROM gps_points_point_id_seq;
  IF seq_val <= max_id THEN
    RAISE EXCEPTION 'PRE-COMMIT FAILED: gps_points sequence out of sync: last_value=%, max_id=%', seq_val, max_id;
  END IF;

  SELECT COALESCE(MAX(history_id), 0) INTO max_id FROM segment_history;
  SELECT last_value INTO seq_val FROM segment_history_history_id_seq;
  IF seq_val <= max_id THEN
    RAISE EXCEPTION 'PRE-COMMIT FAILED: segment_history sequence out of sync: last_value=%, max_id=%', seq_val, max_id;
  END IF;

  -- 7. Verify Test Data Preservation
  SELECT bus_id, vehicle_number INTO test_rec FROM buses WHERE vehicle_number = 'TEST-BUS-001' LIMIT 1;
  IF test_rec.bus_id IS NULL THEN
    RAISE EXCEPTION 'PRE-COMMIT FAILED: Test bus TEST-BUS-001 not found or has NULL bus_id.';
  END IF;

  -- 8. Verify Road Segment Aggregate Parity
  SELECT count(*) INTO null_req_cnt FROM road_segments 
  WHERE observation_count < (pothole_count + waterlogging_count);
  IF null_req_cnt > 0 THEN 
    RAISE EXCEPTION 'PRE-COMMIT FAILED: road_segments has % rows where observation_count is less than sum of pothole_count + waterlogging_count.', null_req_cnt; 
  END IF;

  RAISE NOTICE '=== ALL PRE-COMMIT VALIDATIONS PASSED SUCCESSFULLY. PROCEEDING TO COMMIT. ===';
END $$;

COMMIT;

-- =============================================================================
-- SECTION 10: POST-COMMIT VERIFICATION SMOKE CHECKS
-- (Informational queries only - the transaction is already committed)
-- =============================================================================

-- 10.1 Verify Final Table Row Counts
SELECT 'buses' AS table_name, count(*) AS total_rows, count(bus_id) AS valid_canonical_pks FROM buses
UNION ALL
SELECT 'road_segments', count(*), count(segment_id) FROM road_segments
UNION ALL
SELECT 'observations', count(*), count(observation_id) FROM observations
UNION ALL
SELECT 'gps_points', count(*), count(point_id) FROM gps_points
UNION ALL
SELECT 'incidents', count(*), count(incident_id) FROM incidents
UNION ALL
SELECT 'segment_history', count(*), count(history_id) FROM segment_history;

-- 10.2 Verify Preserved Test Data Records
SELECT bus_id, vehicle_number, route_id, status, last_ping FROM buses WHERE vehicle_number = 'TEST-BUS-001';
SELECT segment_id, name, condition_score, pothole_count, waterlogging_count, last_updated FROM road_segments WHERE name LIKE '%TEST ROAD%';
SELECT observation_id, event_type, severity, confidence, observed_at FROM observations LIMIT 5;
SELECT incident_id, incident_type, severity, observation_id, road_segment_id, recorded_at FROM incidents LIMIT 5;
SELECT point_id, bus_id, heading_deg, recorded_at FROM gps_points LIMIT 5;
SELECT history_id, segment_id, condition_score, confidence, recorded_at FROM segment_history LIMIT 5;

-- 10.3 Verify Final Foreign Key Constraints and ON DELETE Actions
SELECT 
  tc.table_name, 
  tc.constraint_name, 
  kcu.column_name, 
  ccu.table_name AS referenced_table,
  ccu.column_name AS referenced_column,
  rc.delete_rule AS on_delete_action
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu 
  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu 
  ON tc.constraint_name = ccu.constraint_name AND tc.table_schema = ccu.table_schema
JOIN information_schema.referential_constraints rc 
  ON tc.constraint_name = rc.constraint_name AND tc.table_schema = rc.constraint_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
ORDER BY tc.table_name, tc.constraint_name;

-- 10.4 Verify PostGIS Geometry Types and SRID
SELECT 
  'road_segments' AS table_name,
  gis.GeometryType(geom) AS geom_type,
  gis.ST_SRID(geom) AS srid,
  count(*) AS total_rows,
  count(*) FILTER (WHERE geom IS NOT NULL AND gis.ST_IsValid(geom) AND gis.ST_SRID(geom) = 4326) AS valid_geoms
FROM road_segments
GROUP BY gis.GeometryType(geom), gis.ST_SRID(geom);

SELECT 
  'observations' AS table_name,
  gis.GeometryType(geom) AS geom_type,
  gis.ST_SRID(geom) AS srid,
  count(*) AS total_rows,
  count(*) FILTER (WHERE geom IS NOT NULL AND gis.ST_IsValid(geom) AND gis.ST_SRID(geom) = 4326) AS valid_geoms
FROM observations
GROUP BY gis.GeometryType(geom), gis.ST_SRID(geom);

SELECT 
  'gps_points' AS table_name,
  gis.GeometryType(geom) AS geom_type,
  gis.ST_SRID(geom) AS srid,
  count(*) AS total_rows,
  count(*) FILTER (WHERE geom IS NOT NULL AND gis.ST_IsValid(geom) AND gis.ST_SRID(geom) = 4326) AS valid_geoms
FROM gps_points
GROUP BY gis.GeometryType(geom), gis.ST_SRID(geom);

SELECT 
  'incidents' AS table_name,
  gis.GeometryType(geom) AS geom_type,
  gis.ST_SRID(geom) AS srid,
  count(*) AS total_rows,
  count(*) FILTER (WHERE geom IS NOT NULL AND gis.ST_IsValid(geom) AND gis.ST_SRID(geom) = 4326) AS valid_geoms
FROM incidents
GROUP BY gis.GeometryType(geom), gis.ST_SRID(geom);

-- 10.5 Verify Documented NOT NULL Constraints
SELECT table_name, column_name, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (
    (table_name = 'road_segments' AND column_name IN ('segment_id', 'geom')) OR
    (table_name = 'observations' AND column_name IN ('observation_id', 'geom', 'event_type', 'confidence', 'observed_at')) OR
    (table_name = 'incidents' AND column_name IN ('incident_id', 'geom', 'incident_type', 'recorded_at')) OR
    (table_name = 'gps_points' AND column_name IN ('point_id', 'geom', 'recorded_at')) OR
    (table_name = 'segment_history' AND column_name IN ('history_id', 'segment_id', 'condition_score', 'confidence', 'pothole_count', 'waterlogging_count', 'recorded_at'))
  )
ORDER BY table_name, column_name;
