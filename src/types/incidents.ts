export interface Incident {
  incident_id: string;
  incident_type: string;
  incident_score: number;
  severity?: number;
  severity_label?: string;
  description?: string;
  status?: string;
  vehicle_track_id?: string;
  plate_text?: string;
  plate_confidence?: number;
  latitude: number;
  longitude: number;
  timestamp: string;
  road_segment_id?: string | null;
  evidence_uri?: string;
}

