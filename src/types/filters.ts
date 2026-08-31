export interface FilterState {
  layers: {
    roads: boolean;
    events: boolean;
    incidents: boolean;
    buses: boolean;
    heatmap: boolean;
  };
  eventTypes: {
    road_defect: boolean;
    waterlogging: boolean;
    traffic: boolean;
    incident: boolean;
  };
  minSeverity: number;
  minConfidence: number;
}

export const DEFAULT_FILTERS: FilterState = {
  layers: { roads: true, events: true, incidents: true, buses: true, heatmap: false },
  eventTypes: { road_defect: true, waterlogging: true, traffic: true, incident: true },
  minSeverity: 1,
  minConfidence: 0,
};
