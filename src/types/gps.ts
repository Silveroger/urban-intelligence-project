/**
 * SIH 26124: GPS Telemetry & Supabase Ingestion Types
 * Structured contract for collecting, validating, and sending GPS data to Supabase.
 */

export interface GpsRecord {
  id?: string;
  bus_id: string;
  timestamp: string; // ISO 8601 string (timestamptz)
  latitude: number; // double precision [-90, 90]
  longitude: number; // double precision [-180, 180]
  speed: number; // double precision (km/h >= 0)
  heading?: number; // double precision [0, 360)
  location?: string | null; // e.g. "Sector 17, Chandigarh" / "Madhya Marg"
  created_at?: string;
}

export type GpsSyncStatus = 'idle' | 'transmitting' | 'synced' | 'error' | 'duplicate_skipped';

export interface TelemetryStreamItem {
  record: GpsRecord;
  status: GpsSyncStatus;
  statusMessage?: string;
  latencyMs?: number;
  syncedAt?: string;
}

export interface IngestionStats {
  totalTransmitted: number;
  totalSuccess: number;
  totalErrors: number;
  totalDuplicatesSkipped: number;
  lastLatencyMs: number;
  lastSyncTime: string | null;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}
