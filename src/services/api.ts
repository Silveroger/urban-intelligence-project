import axios from 'axios';
import type { RoadSegment } from '../types/roadSegments';
import type { Event } from '../types/events';
import type { Incident } from '../types/incidents';
import type { Bus } from '../types/buses';

// Mock data imports — only used when VITE_USE_MOCK=true
import { mockRoadSegments, mockSegmentHistory } from '../data/mockRoadSegments';
import { mockEvents } from '../data/mockEvents';
import { mockIncidents } from '../data/mockIncidents';
import { mockBuses } from '../data/mockBuses';

const useMock = import.meta.env.VITE_USE_MOCK === 'true';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 10_000,
});

export type SegmentHistory = { date: string; score: number }[];

// §13 — GET /api/v1/segments/geojson
export async function fetchSegments(): Promise<RoadSegment[]> {
  if (useMock) return mockRoadSegments;
  try {
    const { data } = await client.get<any>('/api/v1/segments/geojson');
    // Map GeoJSON FeatureCollection to flat RoadSegment[]
    if (data && data.features && Array.isArray(data.features)) {
      return data.features.map((f: any) => ({
        segment_id: f.properties?.segment_id || f.id,
        name: f.properties?.name || f.properties?.segment_id || f.id,
        geometry: f.geometry?.coordinates || [],
        condition_score: f.properties?.condition_score ?? 100,
        confidence: f.properties?.confidence ?? 1.0,
        pothole_count: f.properties?.pothole_count ?? 0,
        waterlogging_count: f.properties?.waterlogging_count ?? 0,
        observation_count: f.properties?.observation_count ?? 0,
        last_updated: f.properties?.last_updated || new Date().toISOString(),
      }));
    }
    if (Array.isArray(data)) return data;
    return mockRoadSegments;
  } catch (err) {
    console.warn('[API] Failed to fetch segments from backend, falling back to mock fixtures', err);
    return mockRoadSegments;
  }
}

// §13 — GET /api/v1/segments/{segment_id}/history
export async function fetchSegmentHistory(segmentId: string): Promise<SegmentHistory> {
  if (useMock) return mockSegmentHistory[segmentId] ?? [];
  try {
    const { data } = await client.get<any>(`/api/v1/segments/${segmentId}/history`);
    if (Array.isArray(data)) {
      return data.map((item: any) => ({
        date: item.timestamp ? item.timestamp.split('T')[0] : (item.date || ''),
        score: item.condition_score ?? item.score ?? 100,
      }));
    }
    return mockSegmentHistory[segmentId] ?? [];
  } catch {
    return mockSegmentHistory[segmentId] ?? [];
  }
}

// §13 — GET /api/v1/events
export async function fetchEvents(): Promise<Event[]> {
  if (useMock) return mockEvents;
  try {
    const { data } = await client.get<Event[]>('/api/v1/events');
    return Array.isArray(data) ? data : mockEvents;
  } catch {
    return mockEvents;
  }
}

// §13 — GET /api/v1/incidents
export async function fetchIncidents(): Promise<Incident[]> {
  if (useMock) return mockIncidents;
  try {
    const { data } = await client.get<Incident[]>('/api/v1/incidents');
    if (Array.isArray(data)) {
      return data.map((inc: any) => ({
        ...inc,
        incident_score: inc.incident_score ?? (inc.severity ? inc.severity / 4 : 0.8),
      }));
    }
    return mockIncidents;
  } catch {
    return mockIncidents;
  }
}

// §13 — GET /api/v1/buses
export async function fetchBuses(): Promise<Bus[]> {
  if (useMock) return mockBuses;
  try {
    const { data } = await client.get<Bus[]>('/api/v1/buses');
    return Array.isArray(data) ? data : mockBuses;
  } catch {
    return mockBuses;
  }
}
