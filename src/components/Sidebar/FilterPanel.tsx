import { getEventTypeLabel } from '../../utils/formatters';
import type { FilterState } from '../../types/filters';

interface FilterPanelProps {
  filters: FilterState;
  onChange: (f: FilterState) => void;
}

const EVENT_TYPES = ['road_defect', 'waterlogging', 'traffic', 'incident'] as const;

export function FilterPanel({ filters, onChange }: FilterPanelProps) {
  const toggleLayer = (key: keyof FilterState['layers']) => {
    onChange({ ...filters, layers: { ...filters.layers, [key]: !filters.layers[key] } });
  };

  const toggleEventType = (key: keyof FilterState['eventTypes']) => {
    onChange({ ...filters, eventTypes: { ...filters.eventTypes, [key]: !filters.eventTypes[key] } });
  };

  return (
    <div className="filter-panel">
      <h2 className="filter-heading">Filters</h2>

      {/* Layer toggles */}
      <fieldset className="filter-group">
        <legend className="filter-group-label">Map Layers</legend>
        {(Object.keys(filters.layers) as (keyof FilterState['layers'])[]).map((key) => (
          <label key={key} className="filter-toggle">
            <input
              type="checkbox"
              checked={filters.layers[key]}
              onChange={() => toggleLayer(key)}
            />
            <span className="toggle-label">{key.charAt(0).toUpperCase() + key.slice(1)}</span>
          </label>
        ))}
      </fieldset>

      {/* Event type toggles */}
      <fieldset className="filter-group">
        <legend className="filter-group-label">Event Types</legend>
        {EVENT_TYPES.map((t) => (
          <label key={t} className="filter-toggle">
            <input
              type="checkbox"
              checked={filters.eventTypes[t]}
              onChange={() => toggleEventType(t)}
            />
            <span className="toggle-label">{getEventTypeLabel(t)}</span>
          </label>
        ))}
      </fieldset>

      {/* Severity slider */}
      <fieldset className="filter-group">
        <legend className="filter-group-label">
          Min Severity <span className="filter-value">{filters.minSeverity}</span>
        </legend>
        <input
          type="range"
          min={1}
          max={5}
          step={1}
          value={filters.minSeverity}
          onChange={(e) => onChange({ ...filters, minSeverity: Number(e.target.value) })}
          className="filter-slider"
        />
        <div className="slider-labels">
          <span>1</span><span>5</span>
        </div>
      </fieldset>

      {/* Confidence slider */}
      <fieldset className="filter-group">
        <legend className="filter-group-label">
          Min Confidence <span className="filter-value">{Math.round(filters.minConfidence * 100)}%</span>
        </legend>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={filters.minConfidence}
          onChange={(e) => onChange({ ...filters, minConfidence: Number(e.target.value) })}
          className="filter-slider"
        />
        <div className="slider-labels">
          <span>0%</span><span>100%</span>
        </div>
      </fieldset>
    </div>
  );
}
