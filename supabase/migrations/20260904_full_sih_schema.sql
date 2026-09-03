-- ==============================================================================
-- SIH 26124: Complete Urban Intelligence Platform Database Schema
-- Run this script in the Supabase SQL Editor (https://supabase.com/dashboard/project/_/sql)
-- ==============================================================================

-- 0. Enable PostGIS Extension (if available)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS postgis;

-- ------------------------------------------------------------------------------
-- 1. GPS Telemetry Stream Table
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.gps_records (
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

CREATE INDEX IF NOT EXISTS idx_gps_records_timestamp ON public.gps_records (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_gps_records_bus_id_time ON public.gps_records (bus_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_gps_records_lat_lng ON public.gps_records (latitude, longitude);

ALTER TABLE public.gps_records ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public insert to gps_records" ON public.gps_records FOR INSERT TO anon, authenticated WITH CHECK (true);
CREATE POLICY "Allow public select from gps_records" ON public.gps_records FOR SELECT TO anon, authenticated USING (true);


-- ------------------------------------------------------------------------------
-- 2. AI Observations Table (Road Defects, Waterlogging, Infrastructure)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(128) UNIQUE NOT NULL,
    bus_id VARCHAR(64) NOT NULL DEFAULT 'BUS-101',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    class_name VARCHAR(64) NOT NULL,              -- pothole, damaged_road, waterlogging, missing_zebra_crossing, etc.
    event_type VARCHAR(64) NOT NULL DEFAULT 'road_defect', -- road_defect, waterlogging, traffic, etc.
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.85,
    severity INTEGER NOT NULL DEFAULT 2,          -- 1: Minor, 2: Moderate, 3: Severe, 4: Critical
    road_segment_id VARCHAR(64),
    bbox JSONB,                                   -- [x1, y1, x2, y2]
    evidence_image_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_observations_timestamp ON public.observations (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_observations_class ON public.observations (class_name);
CREATE INDEX IF NOT EXISTS idx_observations_severity ON public.observations (severity DESC);
CREATE INDEX IF NOT EXISTS idx_observations_segment ON public.observations (road_segment_id);

ALTER TABLE public.observations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public insert to observations" ON public.observations FOR INSERT TO anon, authenticated WITH CHECK (true);
CREATE POLICY "Allow public select from observations" ON public.observations FOR SELECT TO anon, authenticated USING (true);


-- ------------------------------------------------------------------------------
-- 3. Traffic Incidents Table (Offending Vehicles, Rash Driving, Plate OCR)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id VARCHAR(128) UNIQUE NOT NULL,
    bus_id VARCHAR(64) NOT NULL DEFAULT 'BUS-101',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    incident_type VARCHAR(64) NOT NULL DEFAULT 'rash_driving', -- rash_driving, hit_and_run, illegal_parking
    severity INTEGER NOT NULL DEFAULT 4,
    track_id INTEGER,
    plate_text VARCHAR(32),
    plate_confidence DOUBLE PRECISION DEFAULT 0.50,
    evidence_image_url TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'OPEN',   -- OPEN, UNDER_REVIEW, RESOLVED
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_incidents_timestamp ON public.incidents (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_plate ON public.incidents (plate_text);

ALTER TABLE public.incidents ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public insert to incidents" ON public.incidents FOR INSERT TO anon, authenticated WITH CHECK (true);
CREATE POLICY "Allow public select from incidents" ON public.incidents FOR SELECT TO anon, authenticated USING (true);


-- ------------------------------------------------------------------------------
-- 4. Road Health Aggregated Segments Table
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.road_segments (
    segment_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    road_type VARCHAR(32) DEFAULT 'primary',      -- primary, secondary, arterial
    condition_score DOUBLE PRECISION NOT NULL DEFAULT 100.0, -- 0 (Critical) to 100 (Excellent)
    defect_count INTEGER NOT NULL DEFAULT 0,
    total_passes INTEGER NOT NULL DEFAULT 1,
    last_surveyed TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    geojson_geometry JSONB,                       -- LineString coordinates [[lng, lat], ...]
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE public.road_segments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public select from road_segments" ON public.road_segments FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "Allow public insert/update road_segments" ON public.road_segments FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);


-- ------------------------------------------------------------------------------
-- 5. Enable Supabase Realtime for Live Map & Pipeline Broadcasts
-- ------------------------------------------------------------------------------
-- Adds tables to the realtime publication so web clients receive instant change events
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
