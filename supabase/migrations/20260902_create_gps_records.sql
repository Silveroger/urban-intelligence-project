-- ==============================================================================
-- SIH 26124: Urban Intelligence Platform — GPS Telemetry Ingestion Table
-- Purpose: Persistent storage for GPS telemetry data collected from mobile sensing nodes
-- Handled by Frontend Pipeline -> Consumed by Backend Team for Spatial GIS & Analytics
-- ==============================================================================

-- 1. Create the GPS records table
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

    -- Boundary & sanity constraints
    CONSTRAINT check_latitude_range CHECK (latitude >= -90.0 AND latitude <= 90.0),
    CONSTRAINT check_longitude_range CHECK (longitude >= -180.0 AND longitude <= 180.0),
    CONSTRAINT check_speed_non_negative CHECK (speed >= 0.0)
);

-- 2. Create performance indexes for backend retrieval, time-series, and spatial queries
CREATE INDEX IF NOT EXISTS idx_gps_records_timestamp 
    ON public.gps_records (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_gps_records_bus_id_time 
    ON public.gps_records (bus_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_gps_records_lat_lng 
    ON public.gps_records (latitude, longitude);

-- 3. Enable Row Level Security (RLS)
ALTER TABLE public.gps_records ENABLE ROW LEVEL SECURITY;

-- 4. Create Policies for frontend ingestion and backend read access
-- Allow anonymous/authenticated client insert
CREATE POLICY "Allow public insert to gps_records"
    ON public.gps_records
    FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

-- Allow anonymous/authenticated client select for verification
CREATE POLICY "Allow public read of gps_records"
    ON public.gps_records
    FOR SELECT
    TO anon, authenticated
    USING (true);

-- 5. Optional PostGIS Geometry column & index (if PostGIS extension is enabled by backend)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis') THEN
        -- Add point geometry column if it doesn't already exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'gps_records' AND column_name = 'geom'
        ) THEN
            ALTER TABLE public.gps_records ADD COLUMN geom geometry(Point, 4326);
            -- Auto-populate geom from lat/lng via trigger
            CREATE OR REPLACE FUNCTION public.set_gps_record_geom()
            RETURNS TRIGGER AS $func$
            BEGIN
                NEW.geom = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
                RETURN NEW;
            END;
            $func$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS trg_set_gps_geom ON public.gps_records;
            CREATE TRIGGER trg_set_gps_geom
                BEFORE INSERT OR UPDATE OF latitude, longitude ON public.gps_records
                FOR EACH ROW
                EXECUTE FUNCTION public.set_gps_record_geom();

            CREATE INDEX IF NOT EXISTS idx_gps_records_geom ON public.gps_records USING GIST (geom);
        END IF;
    END IF;
END $$;
