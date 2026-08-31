export function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

export function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`;
}

const EVENT_TYPE_LABELS: Record<string, string> = {
  road_defect: 'Road Defect',
  waterlogging: 'Waterlogging',
  traffic: 'Traffic',
  incident: 'Incident',
};

export function getEventTypeLabel(type: string): string {
  return EVENT_TYPE_LABELS[type] ?? type;
}

const EVENT_TYPE_COLORS: Record<string, string> = {
  road_defect: '#ef4444',   // red
  waterlogging: '#3b82f6',  // blue
  traffic: '#f59e0b',       // amber
  incident: '#a855f7',      // purple
};

export function getEventTypeColor(type: string): string {
  return EVENT_TYPE_COLORS[type] ?? '#6b7280';
}
