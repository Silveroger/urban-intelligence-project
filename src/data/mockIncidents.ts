import type { Incident } from '../types/incidents';

export const mockIncidents: Incident[] = [
  {
    incident_id: 'inc-20260830-001',
    incident_type: 'Wrong-way Driving',
    incident_score: 0.87,
    vehicle_track_id: 'trk-4412',
    plate_text: 'CH-01-AB-1234',
    plate_confidence: 0.74,
    latitude: 30.7340,
    longitude: 76.7830,
    timestamp: '2026-08-30T18:45:00+05:30',
    road_segment_id: 'seg-chd-001',
  },
  {
    incident_id: 'inc-20260830-002',
    incident_type: 'Red-light Violation',
    incident_score: 0.93,
    vehicle_track_id: 'trk-5580',
    plate_text: 'PB-65-C-9876',
    plate_confidence: 0.88,
    latitude: 30.7470,
    longitude: 76.7800,
    timestamp: '2026-08-30T17:30:00+05:30',
    road_segment_id: 'seg-chd-003',
  },
  {
    incident_id: 'inc-20260830-003',
    incident_type: 'Illegal Parking',
    incident_score: 0.65,
    vehicle_track_id: 'trk-6621',
    latitude: 30.7315,
    longitude: 76.7740,
    timestamp: '2026-08-30T19:20:00+05:30',
    road_segment_id: 'seg-chd-004',
  },
];
