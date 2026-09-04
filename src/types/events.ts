export interface Event {
  event_id: string;
  bus_id: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  road_segment_id: string;
  event_type: 'road_defect' | 'waterlogging' | 'traffic' | 'incident' | 'infrastructure' | 'pedestrian';
  class_name?: string;
  confidence: number;
  severity?: number;
  frame_id?: number;
  evidence_uri?: string;
}
