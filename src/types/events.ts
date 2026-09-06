export interface DefectDimensions {
  breadth_cm: number;
  depth_cm: number;
  area_sq_cm?: number;
  bbox_width?: number;
  bbox_height?: number;
}

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
  risk_score?: number;
  risk_level?: 'Low' | 'Moderate' | 'High' | 'Critical' | string;
  breadth_cm?: number;
  depth_cm?: number;
  dimensions?: DefectDimensions;
  risk_assessment?: string;
}
