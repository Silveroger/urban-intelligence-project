export interface RoadSegment {
  segment_id: string;
  name?: string;
  geometry: [number, number][]; // GeoJSON order: [lng, lat]
  condition_score: number;
  confidence: number;
  pothole_count: number;
  waterlogging_count: number;
  observation_count: number;
  last_updated: string;
}
