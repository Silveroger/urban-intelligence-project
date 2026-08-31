import type { RoadSegment } from '../../types/roadSegments';
import type { Event } from '../../types/events';
import type { Incident } from '../../types/incidents';
import type { Bus } from '../../types/buses';
import { getRoadColor } from '../../utils/roadColor';

interface KpiCardsProps {
  segments: RoadSegment[];
  events: Event[];
  incidents: Incident[];
  buses: Bus[];
}

export function KpiCards({ segments, events, incidents, buses }: KpiCardsProps) {
  const avgScore = segments.length
    ? Math.round(segments.reduce((s, r) => s + r.condition_score, 0) / segments.length)
    : 0;
  const criticalCount = segments.filter((r) => r.condition_score < 40).length;

  const cards = [
    { label: 'Road Segments', value: segments.length, color: '#38bdf8' },
    { label: 'Events', value: events.length, color: '#f59e0b' },
    { label: 'Incidents', value: incidents.length, color: '#a855f7' },
    { label: 'Active Buses', value: buses.length, color: '#22c55e' },
    { label: 'Avg Condition', value: avgScore, color: getRoadColor(avgScore) },
    { label: 'Critical Roads', value: criticalCount, color: '#ef4444' },
  ];

  return (
    <div className="kpi-strip">
      {cards.map((c) => (
        <div key={c.label} className="kpi-card">
          <span className="kpi-value" style={{ color: c.color }}>{c.value}</span>
          <span className="kpi-label">{c.label}</span>
        </div>
      ))}
    </div>
  );
}
