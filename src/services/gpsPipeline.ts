import { supabase, isSupabaseConfigured } from './supabase';
import type { GpsRecord, ValidationResult } from '../types/gps';

// Ring buffer of recent signatures to avoid duplicate submissions
const recentSignatures = new Set<string>();
const MAX_SIGNATURE_BUFFER = 500;

function getRecordSignature(record: GpsRecord): string {
  // Quantize coordinates to ~1 meter (5 decimal places) for duplicate detection
  const latRounded = Number(record.latitude).toFixed(5);
  const lngRounded = Number(record.longitude).toFixed(5);
  const timeKey = record.timestamp.slice(0, 19); // YYYY-MM-DDTHH:MM:SS
  return `${record.bus_id}_${latRounded}_${lngRounded}_${timeKey}`;
}

export function validateGpsRecord(record: Partial<GpsRecord>): ValidationResult {
  const errors: string[] = [];

  if (record.latitude === undefined || record.latitude === null || isNaN(Number(record.latitude))) {
    errors.push('Latitude is required and must be a valid number.');
  } else if (record.latitude < -90 || record.latitude > 90) {
    errors.push(`Latitude (${record.latitude}) must be between -90.0 and +90.0 degrees.`);
  }

  if (record.longitude === undefined || record.longitude === null || isNaN(Number(record.longitude))) {
    errors.push('Longitude is required and must be a valid number.');
  } else if (record.longitude < -180 || record.longitude > 180) {
    errors.push(`Longitude (${record.longitude}) must be between -180.0 and +180.0 degrees.`);
  }

  if (record.speed !== undefined && record.speed !== null) {
    if (isNaN(Number(record.speed)) || record.speed < 0) {
      errors.push(`Speed (${record.speed}) cannot be negative.`);
    }
  }

  if (!record.bus_id || record.bus_id.trim() === '') {
    errors.push('Vehicle/Bus ID is required.');
  }

  if (record.timestamp) {
    const d = new Date(record.timestamp);
    if (isNaN(d.getTime())) {
      errors.push(`Invalid timestamp format: "${record.timestamp}". Must be valid ISO 8601 string.`);
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

export function isDuplicateRecord(record: GpsRecord): boolean {
  const sig = getRecordSignature(record);
  if (recentSignatures.has(sig)) {
    return true;
  }
  if (recentSignatures.size >= MAX_SIGNATURE_BUFFER) {
    // Evict earliest
    const first = recentSignatures.values().next().value;
    if (first) recentSignatures.delete(first);
  }
  recentSignatures.add(sig);
  return false;
}

/**
 * Inserts a single validated GPS record directly into Supabase `gps_records` table.
 */
export async function insertGpsRecord(record: GpsRecord): Promise<{
  success: boolean;
  data?: GpsRecord;
  error?: string;
  latencyMs: number;
  duplicateSkipped?: boolean;
}> {
  const validation = validateGpsRecord(record);
  if (!validation.valid) {
    return {
      success: false,
      error: `Validation Failed: ${validation.errors.join(' ')}`,
      latencyMs: 0,
    };
  }

  if (isDuplicateRecord(record)) {
    return {
      success: true,
      data: record,
      duplicateSkipped: true,
      latencyMs: 0,
      error: 'Duplicate GPS point skipped (already transmitted recently).',
    };
  }

  const payload = {
    bus_id: record.bus_id,
    timestamp: record.timestamp || new Date().toISOString(),
    latitude: Number(record.latitude),
    longitude: Number(record.longitude),
    speed: Number(record.speed ?? 0.0),
    heading: Number(record.heading ?? 0.0),
    location: record.location || null,
  };

  const startTime = performance.now();

  if (!isSupabaseConfigured) {
    // Simulated offline confirmation if Supabase credentials are not yet entered
    console.info('[GPS Pipeline (Local Simulated Mode)] Record prepared for Supabase:', payload);
    const latency = Math.round(performance.now() - startTime + Math.random() * 40 + 20);
    return {
      success: true,
      data: { ...payload, id: `local_sim_${Date.now()}` },
      latencyMs: latency,
    };
  }

  try {
    const { data, error } = await supabase
      .from('gps_records')
      .insert([payload])
      .select()
      .single();

    const latency = Math.round(performance.now() - startTime);

    if (error) {
      console.error('[GPS Pipeline] Supabase insert failed:', error);
      return {
        success: false,
        error: `Supabase Error (${error.code || 'ERR'}): ${error.message}`,
        latencyMs: latency,
      };
    }

    return {
      success: true,
      data: data as GpsRecord,
      latencyMs: latency,
    };
  } catch (err: unknown) {
    const latency = Math.round(performance.now() - startTime);
    const errMsg = err instanceof Error ? err.message : 'Failed to communicate with Supabase';
    console.error('[GPS Pipeline] Network/Client exception:', err);
    return {
      success: false,
      error: errMsg,
      latencyMs: latency,
    };
  }
}

/**
 * Batch insert multiple GPS records into Supabase `gps_records`.
 */
export async function insertGpsBatch(records: GpsRecord[]): Promise<{
  total: number;
  successCount: number;
  errorCount: number;
  errors: string[];
}> {
  const validRecords: Array<{
    bus_id: string;
    timestamp: string;
    latitude: number;
    longitude: number;
    speed: number;
    heading: number;
    location: string | null;
  }> = [];
  const errors: string[] = [];

  for (let i = 0; i < records.length; i++) {
    const rec = records[i];
    const val = validateGpsRecord(rec);
    if (!val.valid) {
      errors.push(`Row ${i + 1}: ${val.errors.join('; ')}`);
    } else {
      validRecords.push({
        bus_id: rec.bus_id || 'BUS-101',
        timestamp: rec.timestamp || new Date().toISOString(),
        latitude: Number(rec.latitude),
        longitude: Number(rec.longitude),
        speed: Number(rec.speed ?? 0.0),
        heading: Number(rec.heading ?? 0.0),
        location: rec.location || null,
      });
    }
  }

  if (validRecords.length === 0) {
    return {
      total: records.length,
      successCount: 0,
      errorCount: errors.length,
      errors,
    };
  }

  if (!isSupabaseConfigured) {
    console.info(`[GPS Pipeline] Batch of ${validRecords.length} records processed locally (Simulated Mode).`);
    return {
      total: records.length,
      successCount: validRecords.length,
      errorCount: errors.length,
      errors,
    };
  }

  try {
    const { error } = await supabase.from('gps_records').insert(validRecords);
    if (error) {
      errors.push(`Supabase batch error: ${error.message}`);
      return {
        total: records.length,
        successCount: 0,
        errorCount: records.length,
        errors,
      };
    }

    return {
      total: records.length,
      successCount: validRecords.length,
      errorCount: errors.length,
      errors,
    };
  } catch (err: unknown) {
    const errMsg = err instanceof Error ? err.message : 'Supabase request failed';
    errors.push(errMsg);
    return {
      total: records.length,
      successCount: 0,
      errorCount: records.length,
      errors,
    };
  }
}

/**
 * Fetches recent records directly from Supabase for verification.
 */
export async function fetchRecentGpsRecords(limit = 25): Promise<GpsRecord[]> {
  if (!isSupabaseConfigured) return [];
  try {
    const { data, error } = await supabase
      .from('gps_records')
      .select('*')
      .order('timestamp', { ascending: false })
      .limit(limit);

    if (error) {
      console.warn('[GPS Pipeline] fetchRecentGpsRecords error:', error);
      return [];
    }
    return (data as GpsRecord[]) || [];
  } catch (err) {
    console.warn('[GPS Pipeline] Failed to query Supabase records:', err);
    return [];
  }
}

/**
 * Parses GPS files (.json, .csv) into structured GpsRecord array
 */
export async function parseGpsFile(file: File, defaultBusId = 'BUS-101'): Promise<GpsRecord[]> {
  const text = await file.text();
  const name = file.name.toLowerCase();

  if (name.endsWith('.json')) {
    try {
      const parsed = JSON.parse(text);
      const list: Array<Record<string, unknown>> = Array.isArray(parsed)
        ? parsed
        : ((parsed.points || parsed.records || parsed.data || [parsed]) as Array<Record<string, unknown>>);
      return list.map((item, idx) => ({
        bus_id: (item.bus_id as string) || defaultBusId,
        timestamp:
          (item.timestamp as string) ||
          (item.recorded_at as string) ||
          (item.time as string) ||
          new Date(Date.now() + idx * 1000).toISOString(),
        latitude: Number(item.latitude ?? item.lat ?? item.y),
        longitude: Number(item.longitude ?? item.lng ?? item.lon ?? item.x),
        speed: Number(item.speed ?? item.velocity ?? 30),
        heading: Number(item.heading ?? item.heading_deg ?? item.bearing ?? 0),
        location: (item.location as string) ?? (item.sector as string) ?? (item.name as string) ?? undefined,
      }));
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Invalid JSON format';
      throw new Error(`Invalid JSON GPS file: ${msg}`, { cause: e });
    }
  }

  if (name.endsWith('.csv') || name.endsWith('.txt')) {
    const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
    if (lines.length < 2) {
      throw new Error('CSV file is empty or missing headers.');
    }
    const headers = lines[0].split(',').map((h) => h.trim().toLowerCase());
    const latIdx = headers.findIndex((h) => h === 'latitude' || h === 'lat' || h === 'y');
    const lngIdx = headers.findIndex((h) => h === 'longitude' || h === 'lng' || h === 'lon' || h === 'x');
    const timeIdx = headers.findIndex((h) => h === 'timestamp' || h === 'time' || h === 'recorded_at');
    const speedIdx = headers.findIndex((h) => h === 'speed' || h === 'velocity');
    const headingIdx = headers.findIndex((h) => h === 'heading' || h === 'heading_deg' || h === 'bearing');
    const locIdx = headers.findIndex((h) => h === 'location' || h === 'sector' || h === 'zone');
    const busIdx = headers.findIndex((h) => h === 'bus_id' || h === 'vehicle_id' || h === 'bus');

    if (latIdx === -1 || lngIdx === -1) {
      throw new Error('CSV must have "latitude" and "longitude" columns.');
    }

    const records: GpsRecord[] = [];
    for (let i = 1; i < lines.length; i++) {
      const cols = lines[i].split(',').map((c) => c.trim());
      if (cols.length <= Math.max(latIdx, lngIdx)) continue;
      const lat = parseFloat(cols[latIdx]);
      const lng = parseFloat(cols[lngIdx]);
      if (isNaN(lat) || isNaN(lng)) continue;

      records.push({
        bus_id: busIdx >= 0 && cols[busIdx] ? cols[busIdx] : defaultBusId,
        timestamp: timeIdx >= 0 && cols[timeIdx] ? cols[timeIdx] : new Date(Date.now() + i * 1000).toISOString(),
        latitude: lat,
        longitude: lng,
        speed: speedIdx >= 0 && !isNaN(parseFloat(cols[speedIdx])) ? parseFloat(cols[speedIdx]) : 35.0,
        heading: headingIdx >= 0 && !isNaN(parseFloat(cols[headingIdx])) ? parseFloat(cols[headingIdx]) : 0,
        location: locIdx >= 0 && cols[locIdx] ? cols[locIdx] : undefined,
      });
    }
    return records;
  }

  throw new Error('Unsupported file format. Please upload a .json or .csv GPS log file.');
}

/**
 * Built-in synthetic GPS trajectory generator for Chandigarh Sensing Routes
 */
export const CHANDIGARH_GPS_WAYPOINTS: Array<{ lat: number; lng: number; location: string; speed: number }> = [
  { lat: 30.7352, lng: 76.7821, location: 'Sector 17 City Centre Plaza', speed: 28.5 },
  { lat: 30.7378, lng: 76.7845, location: 'Sector 17 / 18 Crossing', speed: 34.2 },
  { lat: 30.7410, lng: 76.7880, location: 'Madhya Marg (Eastbound)', speed: 45.0 },
  { lat: 30.7445, lng: 76.7915, location: 'Sector 8 / 9 Light Point', speed: 42.1 },
  { lat: 30.7480, lng: 76.7950, location: 'Matka Chowk (Roundabout)', speed: 22.4 },
  { lat: 30.7512, lng: 76.7988, location: 'Sector 10 Heritage Corridor', speed: 38.6 },
  { lat: 30.7545, lng: 76.7720, location: 'PGIMER Main Gate', speed: 25.0 },
  { lat: 30.7300, lng: 76.7750, location: 'Aroma Chowk (Sector 22)', speed: 30.8 },
  { lat: 30.7220, lng: 76.7680, location: 'ISBT 43 Bus Terminal Approach', speed: 36.4 },
  { lat: 30.7180, lng: 76.7610, location: 'Sector 35 Commercial District', speed: 29.2 },
  { lat: 30.7250, lng: 76.7530, location: 'Dakhshin Marg Boulevard', speed: 48.0 },
];

export function generateNextSimulatedGps(
  busId: string,
  currentIndex: number
): { record: GpsRecord; nextIndex: number } {
  const wp = CHANDIGARH_GPS_WAYPOINTS[currentIndex % CHANDIGARH_GPS_WAYPOINTS.length];
  const nextIndex = (currentIndex + 1) % CHANDIGARH_GPS_WAYPOINTS.length;
  const nextWp = CHANDIGARH_GPS_WAYPOINTS[nextIndex];

  // Add small realistic GPS jitter (+/- 0.0001 deg ~ 10m)
  const jitterLat = (Math.random() - 0.5) * 0.00015;
  const jitterLng = (Math.random() - 0.5) * 0.00015;
  const speedVariation = (Math.random() - 0.5) * 4.0;

  // Compute rough bearing/heading to next point
  const y = Math.sin((nextWp.lng - wp.lng) * (Math.PI / 180)) * Math.cos(nextWp.lat * (Math.PI / 180));
  const x =
    Math.cos(wp.lat * (Math.PI / 180)) * Math.sin(nextWp.lat * (Math.PI / 180)) -
    Math.sin(wp.lat * (Math.PI / 180)) * Math.cos(nextWp.lat * (Math.PI / 180)) * Math.cos((nextWp.lng - wp.lng) * (Math.PI / 180));
  const heading = Math.round((Math.atan2(y, x) * (180 / Math.PI) + 360) % 360);

  const record: GpsRecord = {
    bus_id: busId,
    timestamp: new Date().toISOString(),
    latitude: parseFloat((wp.lat + jitterLat).toFixed(6)),
    longitude: parseFloat((wp.lng + jitterLng).toFixed(6)),
    speed: parseFloat(Math.max(0, wp.speed + speedVariation).toFixed(1)),
    heading,
    location: wp.location,
  };

  return { record, nextIndex };
}
