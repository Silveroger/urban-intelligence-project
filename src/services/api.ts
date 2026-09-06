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

export interface AnalyticsSummary {
  total_segments: number;
  average_condition_score: number;
  critical_segments_count: number;
  active_buses_count: number;
  total_events_count: number;
  total_incidents_count: number;
  condition_distribution: {
    healthy: number;
    moderate: number;
    poor: number;
    critical: number;
  };
}

// §13 — GET /api/v1/segments/geojson
export async function fetchSegments(): Promise<RoadSegment[]> {
  if (useMock) return mockRoadSegments;
  try {
    const { data } = await client.get<any>('/api/v1/segments/geojson');
    if (Array.isArray(data)) {
      return data;
    }
    if (data && Array.isArray(data.features)) {
      return data.features.map((f: any) => ({
        segment_id: f.properties?.segment_id || f.id || '',
        name: f.properties?.name || 'Road Segment',
        geometry: f.geometry?.coordinates || [],
        condition_score: Number(f.properties?.condition_score ?? 100),
        confidence: Number(f.properties?.confidence ?? 1.0),
        pothole_count: Number(f.properties?.pothole_count ?? 0),
        waterlogging_count: Number(f.properties?.waterlogging_count ?? 0),
        observation_count: Number(f.properties?.observation_count ?? 0),
        last_updated: f.properties?.last_updated || '',
      }));
    }
    return [];
  } catch (err) {
    console.error('Failed to fetch road segments from backend:', err);
    return [];
  }
}

// §13 — GET /api/v1/segments/{segment_id}/history
export async function fetchSegmentHistory(segmentId: string): Promise<SegmentHistory> {
  if (useMock) return mockSegmentHistory[segmentId] ?? [];
  try {
    const { data } = await client.get<any[]>(`/api/v1/segments/${segmentId}/history`);
    return data.map((item) => ({
      date: item.date || item.timestamp || '',
      score: Number(item.score ?? item.condition_score ?? 100),
    }));
  } catch (err) {
    console.warn(`Failed to fetch history for segment ${segmentId}:`, err);
    return [];
  }
}

// §13 — GET /api/v1/events
export async function fetchEvents(): Promise<Event[]> {
  if (useMock) return mockEvents;
  try {
    const { data } = await client.get<Event[]>('/api/v1/events');
    return data;
  } catch (err) {
    console.error('Failed to fetch events from backend:', err);
    return [];
  }
}

// §13 — GET /api/v1/incidents
export async function fetchIncidents(): Promise<Incident[]> {
  if (useMock) return mockIncidents;
  try {
    const { data } = await client.get<Incident[]>('/api/v1/incidents');
    return data;
  } catch (err) {
    console.error('Failed to fetch incidents from backend:', err);
    return [];
  }
}

// §13 — GET /api/v1/buses
export async function fetchBuses(): Promise<Bus[]> {
  if (useMock) return mockBuses;
  try {
    const { data } = await client.get<Bus[]>('/api/v1/buses');
    return data;
  } catch (err) {
    console.error('Failed to fetch buses from backend:', err);
    return [];
  }
}

// GET /api/v1/analytics/summary
export async function fetchAnalyticsSummary(): Promise<AnalyticsSummary | null> {
  try {
    const { data } = await client.get<AnalyticsSummary>('/api/v1/analytics/summary');
    return data;
  } catch (err) {
    console.warn('Failed to fetch analytics summary:', err);
    return null;
  }
}
