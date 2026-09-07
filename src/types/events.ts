export interface Event {
  event_id: string;
  bus_id: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  road_segment_id: string;
  event_type: 'road_defect' | 'waterlogging' | 'traffic' | 'incident';
  class_name?: string;
  confidence: number;
  severity?: number;
  severity_label?: string;
  frame_id?: number;
  evidence_uri?: string;
  risk_score?: number;
  risk_level?: string;
  breadth_cm?: number;
  depth_cm?: number;
  dimensions?: {
    breadth_cm?: number;
    depth_cm?: number;
    [key: string]: any;
  };
  risk_assessment?: string;
  metadata?: Record<string, any>;
}
