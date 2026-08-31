import type { RoadSegment } from '../../types/roadSegments';
import type { Event } from '../../types/events';
import type { Incident } from '../../types/incidents';
import { getRoadColor, getRoadStatusLabel } from '../../utils/roadColor';
import { formatTimestamp, formatConfidence, getEventTypeLabel } from '../../utils/formatters';
import { ConditionHistory } from '../Analytics/ConditionHistory';

interface InspectorProps {
  selectedRoad: RoadSegment | null;
  selectedEvent: Event | null;
  selectedIncident: Incident | null;
  segmentHistory: { date: string; score: number }[];
  onClose: () => void;
}

export function Inspector({ selectedRoad, selectedEvent, selectedIncident, segmentHistory, onClose }: InspectorProps) {
  if (!selectedRoad && !selectedEvent && !selectedIncident) {
    return (
      <div className="inspector-panel empty">
        <p className="inspector-placeholder">
          Click a road segment, event marker, or incident on the map to inspect details.
        </p>
      </div>
    );
  }

  const typeLabel = selectedRoad
    ? 'Road Segment'
    : selectedEvent
      ? 'Event'
      : 'Incident';

  const title = selectedRoad
    ? (selectedRoad.name || selectedRoad.segment_id)
    : selectedEvent
      ? (selectedEvent.class_name || getEventTypeLabel(selectedEvent.event_type))
      : selectedIncident!.incident_type;

  return (
    <div className="inspector-panel">
      <div className="inspector-header">
        <div className="inspector-title-area">
          <span className="inspector-type-badge">{typeLabel}</span>
          <h3 className="inspector-title">{title}</h3>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="inspector-close-btn"
          aria-label="Close Inspector"
        >
          ✕
        </button>
      </div>

      <div className="inspector-body">
        {/* ─── Road Segment ─── */}
        {selectedRoad && (
          <div className="inspector-section">
            <div className="inspector-score-card">
              <div className="score-label">Condition Score</div>
              <div
                className="score-value"
                style={{ color: getRoadColor(selectedRoad.condition_score) }}
              >
                {selectedRoad.condition_score}
                <span className="score-max">/100</span>
              </div>
              <div
                className="score-status-pill"
                style={{
                  backgroundColor: `${getRoadColor(selectedRoad.condition_score)}22`,
                  borderColor: getRoadColor(selectedRoad.condition_score),
                  color: getRoadColor(selectedRoad.condition_score),
                }}
              >
                {getRoadStatusLabel(selectedRoad.condition_score)}
              </div>
            </div>

            <div className="inspector-grid">
              <Field label="Segment ID" value={selectedRoad.segment_id} mono />
              <Field label="Confidence" value={formatConfidence(selectedRoad.confidence)} />
              <Field label="Potholes Detected" value={selectedRoad.pothole_count} />
              <Field label="Waterlogging Incidents" value={selectedRoad.waterlogging_count} />
              <Field label="Observations (Passes)" value={selectedRoad.observation_count} />
              <Field label="Last Updated" value={formatTimestamp(selectedRoad.last_updated)} />
            </div>

            <ConditionHistory history={segmentHistory} />
          </div>
        )}

        {/* ─── Event ─── */}
        {selectedEvent && (
          <div className="inspector-section">
            <div className="inspector-grid">
              <Field label="Event ID" value={selectedEvent.event_id} mono />
              <Field label="Event Type" value={getEventTypeLabel(selectedEvent.event_type)} />
              <Field
                label="Severity"
                value={selectedEvent.severity !== undefined ? `Level ${selectedEvent.severity}` : 'N/A'}
              />
              <Field label="Confidence" value={formatConfidence(selectedEvent.confidence)} />
              <Field label="Vehicle / Bus ID" value={selectedEvent.bus_id} mono />
              <Field label="Matched Segment" value={selectedEvent.road_segment_id} mono />
              <Field
                label="Coordinates"
                value={`${selectedEvent.latitude.toFixed(5)}, ${selectedEvent.longitude.toFixed(5)}`}
                mono
              />
              <Field label="Detected At" value={formatTimestamp(selectedEvent.timestamp)} />
            </div>
          </div>
        )}

        {/* ─── Incident ─── */}
        {selectedIncident && (
          <div className="inspector-section">
            <div className="inspector-score-card">
              <div className="score-label">Incident Score</div>
              <div className="score-value" style={{ color: '#f43f5e' }}>
                {Math.round(selectedIncident.incident_score * 100)}
                <span className="score-max">%</span>
              </div>
            </div>

            <div className="inspector-grid">
              <Field label="Incident ID" value={selectedIncident.incident_id} mono />
              <Field label="Incident Type" value={selectedIncident.incident_type} />
              {selectedIncident.vehicle_track_id && (
                <Field label="Vehicle Track ID" value={selectedIncident.vehicle_track_id} mono />
              )}
              {selectedIncident.plate_text && (
                <Field
                  label="Plate Text"
                  value={
                    `${selectedIncident.plate_text} (${formatConfidence(selectedIncident.plate_confidence ?? 0)} conf.)`
                  }
                  mono
                />
              )}
              <Field label="Matched Segment" value={selectedIncident.road_segment_id} mono />
              <Field
                label="Coordinates"
                value={`${selectedIncident.latitude.toFixed(5)}, ${selectedIncident.longitude.toFixed(5)}`}
                mono
              />
              <Field label="Detected At" value={formatTimestamp(selectedIncident.timestamp)} />
            </div>

            {selectedIncident.plate_text && (
              <p className="plate-caveat">
                ⚠ Plate text is OCR-derived and may not be fully accurate. Confidence shown above.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/** Reusable inspector field to reduce repetition */
function Field({ label, value, mono }: { label: string; value: string | number; mono?: boolean }) {
  return (
    <div className="inspector-field">
      <span className="field-label">{label}</span>
      <span className={`field-value${mono ? ' font-mono' : ''}`}>{value}</span>
    </div>
  );
}
