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
  const { data } = await client.get<RoadSegment[]>('/api/v1/segments/geojson');
  return data;
}

// §13 — GET /api/v1/segments/{segment_id}/history
export async function fetchSegmentHistory(segmentId: string): Promise<SegmentHistory> {
  if (useMock) return mockSegmentHistory[segmentId] ?? [];
  const { data } = await client.get<SegmentHistory>(`/api/v1/segments/${segmentId}/history`);
  return data;
}

// §13 — GET /api/v1/events
export async function fetchEvents(): Promise<Event[]> {
  if (useMock) return mockEvents;
  const { data } = await client.get<Event[]>('/api/v1/events');
  return data;
}

// §13 — GET /api/v1/incidents
export async function fetchIncidents(): Promise<Incident[]> {
  if (useMock) return mockIncidents;
  const { data } = await client.get<Incident[]>('/api/v1/incidents');
  return data;
}

// §13 — GET /api/v1/buses
export async function fetchBuses(): Promise<Bus[]> {
  if (useMock) return mockBuses;
  const { data } = await client.get<Bus[]>('/api/v1/buses');
  return data;
}
