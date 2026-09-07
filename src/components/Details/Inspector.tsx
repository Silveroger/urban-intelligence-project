import type { RoadSegment } from '../../types/roadSegments';
import type { Event } from '../../types/events';
import type { Incident } from '../../types/incidents';
import type { Bus } from '../../types/buses';
import { getRoadColor, getRoadStatusLabel } from '../../utils/roadColor';
import { formatTimestamp, formatConfidence, getEventTypeLabel } from '../../utils/formatters';
import { ConditionHistory } from '../Analytics/ConditionHistory';
import { AlertTriangle, Camera, Image as ImageIcon } from 'lucide-react';

const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function getHeadingDescription(deg?: number): string {
  if (deg == null) return 'N/A';
  const dirs = ['North (N)', 'North-East (NE)', 'East (E)', 'South-East (SE)', 'South (S)', 'South-West (SW)', 'West (W)', 'North-West (NW)'];
  const idx = Math.round(((deg % 360) / 45)) % 8;
  return `${Math.round(deg)}° — ${dirs[idx]}`;
}

interface InspectorProps {
  selectedRoad: RoadSegment | null;
  selectedEvent: Event | null;
  selectedIncident: Incident | null;
  selectedBus?: Bus | null;
  segmentHistory: { date: string; score: number }[];
  onClose: () => void;
}

export function Inspector({
  selectedRoad,
  selectedEvent,
  selectedIncident,
  selectedBus,
  segmentHistory,
  onClose,
}: InspectorProps) {
  if (!selectedRoad && !selectedEvent && !selectedIncident && !selectedBus) {
    return (
      <div className="inspector-panel empty">
        <p className="inspector-placeholder">
          Click a road segment, bus marker, event pin, or traffic incident on the map to inspect details.
        </p>
      </div>
    );
  }

  const typeLabel = selectedRoad
    ? 'Road Segment'
    : selectedEvent
      ? 'Event'
      : selectedIncident
        ? 'Incident'
        : 'Fleet Bus';

  const title = selectedRoad
    ? (selectedRoad.name || selectedRoad.segment_id)
    : selectedEvent
      ? (selectedEvent.class_name || getEventTypeLabel(selectedEvent.event_type))
      : selectedIncident
        ? selectedIncident.incident_type
        : (selectedBus?.vehicle_number || selectedBus?.bus_id || 'Bus');


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
            {selectedEvent.risk_score !== undefined && (
              <div className="inspector-score-card">
                <div className="score-label">Defect Risk Index</div>
                <div
                  className="score-value"
                  style={{
                    color:
                      selectedEvent.risk_score >= 80
                        ? '#ef4444'
                        : selectedEvent.risk_score >= 50
                          ? '#f97316'
                          : '#eab308',
                  }}
                >
                  {Math.round(selectedEvent.risk_score)}
                  <span className="score-max">/100</span>
                </div>
                {selectedEvent.risk_level && (
                  <div
                    className="score-status-pill"
                    style={{
                      backgroundColor:
                        selectedEvent.risk_score >= 80
                          ? 'rgba(239, 68, 68, 0.15)'
                          : selectedEvent.risk_score >= 50
                            ? 'rgba(249, 115, 22, 0.15)'
                            : 'rgba(234, 179, 8, 0.15)',
                      borderColor:
                        selectedEvent.risk_score >= 80
                          ? '#ef4444'
                          : selectedEvent.risk_score >= 50
                            ? '#f97316'
                            : '#eab308',
                      color:
                        selectedEvent.risk_score >= 80
                          ? '#ef4444'
                          : selectedEvent.risk_score >= 50
                            ? '#f97316'
                            : '#eab308',
                    }}
                  >
                    {selectedEvent.risk_level.toUpperCase()}
                  </div>
                )}
              </div>
            )}

            <div className="inspector-grid">
              <Field label="Event ID" value={selectedEvent.event_id} mono />
              <Field label="Event Type" value={getEventTypeLabel(selectedEvent.event_type)} />
              <Field
                label="Severity"
                value={selectedEvent.severity !== undefined ? `Level ${selectedEvent.severity}` : 'N/A'}
              />
              <Field label="Confidence" value={formatConfidence(selectedEvent.confidence)} />
              {(selectedEvent.breadth_cm != null || selectedEvent.dimensions?.breadth_cm != null) && (
                <Field
                  label="Est. Breadth"
                  value={`${selectedEvent.breadth_cm ?? selectedEvent.dimensions?.breadth_cm} cm`}
                />
              )}
              {(selectedEvent.depth_cm != null || selectedEvent.dimensions?.depth_cm != null) && (
                <Field
                  label="Est. Depth"
                  value={`${selectedEvent.depth_cm ?? selectedEvent.dimensions?.depth_cm} cm`}
                />
              )}
              <Field label="Vehicle / Bus ID" value={selectedEvent.bus_id} mono />
              <Field label="Matched Segment" value={selectedEvent.road_segment_id} mono />
              <Field
                label="Coordinates"
                value={`${selectedEvent.latitude.toFixed(5)}, ${selectedEvent.longitude.toFixed(5)}`}
                mono
              />
              <Field label="Detected At" value={formatTimestamp(selectedEvent.timestamp)} />
            </div>

            {selectedEvent.risk_assessment && (
              <div style={{ marginTop: '12px', padding: '12px', background: 'rgba(15, 23, 42, 0.85)', borderRadius: '10px', border: '1px solid #334155' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#fbbf24', fontSize: '11px', fontWeight: 700, marginBottom: '4px', textTransform: 'uppercase' }}>
                  <AlertTriangle style={{ width: 14, height: 14 }} />
                  <span>Civil Hazard Diagnostic</span>
                </div>
                <p style={{ color: '#cbd5e1', fontSize: '12px', lineHeight: '1.4' }}>
                  {selectedEvent.risk_assessment}
                </p>
              </div>
            )}

            {selectedEvent.evidence_uri && (
              <div style={{ marginTop: '12px', padding: '12px', background: 'rgba(15, 23, 42, 0.85)', borderRadius: '10px', border: '1px solid #334155' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#818cf8', fontSize: '11px', fontWeight: 700, marginBottom: '8px', textTransform: 'uppercase' }}>
                  <Camera style={{ width: 14, height: 14 }} />
                  <span>Keyframe Evidence Crop</span>
                </div>
                <img
                  src={selectedEvent.evidence_uri.startsWith('http') ? selectedEvent.evidence_uri : `${baseUrl}${selectedEvent.evidence_uri}`}
                  alt="Defect Evidence Crop"
                  style={{ width: '100%', maxHeight: '180px', objectFit: 'cover', borderRadius: '8px', border: '1px solid #334155' }}
                  onError={(e) => {
                    (e.target as HTMLElement).style.display = 'none';
                  }}
                />
              </div>
            )}
          </div>
        )}

        {/* ─── Incident ─── */}
        {selectedIncident && (() => {
          const scoreVal = selectedIncident.incident_score > 1
            ? Math.round(selectedIncident.incident_score)
            : Math.round((selectedIncident.incident_score ?? 0) * 100);
          return (
            <div className="inspector-section">
              <div className="inspector-score-card">
                <div className="score-label">Incident Severity Score</div>
                <div className="score-value" style={{ color: '#f43f5e' }}>
                  {scoreVal}
                  <span className="score-max">/100</span>
                </div>
                {selectedIncident.severity_label && (
                  <div
                    className="score-status-pill"
                    style={{
                      backgroundColor: 'rgba(244, 63, 94, 0.15)',
                      borderColor: '#f43f5e',
                      color: '#f43f5e',
                    }}
                  >
                    {selectedIncident.severity_label.toUpperCase()}
                  </div>
                )}
              </div>

              <div className="inspector-grid">
                <Field label="Incident ID" value={selectedIncident.incident_id} mono />
                <Field label="Incident Type" value={selectedIncident.incident_type} />
                {selectedIncident.severity !== undefined && (
                  <Field label="Severity Rating" value={`Level ${selectedIncident.severity} of 4`} />
                )}
                {selectedIncident.status && (
                  <Field label="Case Status" value={selectedIncident.status.toUpperCase()} />
                )}
                {selectedIncident.vehicle_track_id && (
                  <Field label="Vehicle Track ID" value={selectedIncident.vehicle_track_id} mono />
                )}
                {selectedIncident.plate_text && (
                  <Field
                    label="Plate Text (OCR)"
                    value={
                      `${selectedIncident.plate_text} (${formatConfidence(selectedIncident.plate_confidence ?? 0)} conf.)`
                    }
                    mono
                  />
                )}
                <Field label="Matched Segment" value={selectedIncident.road_segment_id || 'Unmatched'} mono />
                <Field
                  label="Coordinates"
                  value={`${selectedIncident.latitude.toFixed(5)}, ${selectedIncident.longitude.toFixed(5)}`}
                  mono
                />
                <Field label="Detected At" value={formatTimestamp(selectedIncident.timestamp)} />
              </div>

              {selectedIncident.description && (
                <p style={{ marginTop: '12px', fontSize: '12px', color: '#cbd5e1', lineHeight: '1.4' }}>
                  <strong>Description:</strong> {selectedIncident.description}
                </p>
              )}

              {selectedIncident.plate_text && (
                <p className="plate-caveat">
                  ⚠ Plate text is OCR-derived and may not be fully accurate. Confidence shown above.
                </p>
              )}

              {selectedIncident.evidence_uri && (
                <div style={{ marginTop: '12px', padding: '12px', background: 'rgba(15, 23, 42, 0.85)', borderRadius: '10px', border: '1px solid #334155' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#f43f5e', fontSize: '11px', fontWeight: 700, marginBottom: '8px', textTransform: 'uppercase' }}>
                    <ImageIcon style={{ width: 14, height: 14 }} />
                    <span>Incident Evidence Crop</span>
                  </div>
                  <img
                    src={selectedIncident.evidence_uri.startsWith('http') ? selectedIncident.evidence_uri : `${baseUrl}${selectedIncident.evidence_uri}`}
                    alt="Incident Evidence Crop"
                    style={{ width: '100%', maxHeight: '180px', objectFit: 'cover', borderRadius: '8px', border: '1px solid #334155' }}
                    onError={(e) => {
                      (e.target as HTMLElement).style.display = 'none';
                    }}
                  />
                </div>
              )}
            </div>
          );
        })()}

        {/* ─── Fleet Bus ─── */}
        {selectedBus && (
          <div className="inspector-section">
            <div className="inspector-score-card">
              <div className="score-label">Fleet Status</div>
              <div className="score-value" style={{ color: '#22c55e' }}>
                {selectedBus.status ? selectedBus.status.toUpperCase() : 'ACTIVE'}
              </div>
              <div
                className="score-status-pill"
                style={{
                  backgroundColor: 'rgba(34, 197, 94, 0.15)',
                  borderColor: '#22c55e',
                  color: '#22c55e',
                }}
              >
                LIVE SENSING
              </div>
            </div>

            <div className="inspector-grid">
              <Field label="Bus Identifier" value={selectedBus.bus_id} mono />
              <Field label="Vehicle Number" value={selectedBus.vehicle_number || selectedBus.bus_id} mono />
              <Field
                label="Current Speed"
                value={selectedBus.speed_kmh != null ? `${Math.round(selectedBus.speed_kmh)} km/h` : '32 km/h'}
              />
              <Field label="Heading / Direction" value={getHeadingDescription(selectedBus.heading_deg)} />
              <Field
                label="Coordinates"
                value={`${selectedBus.latitude.toFixed(5)}, ${selectedBus.longitude.toFixed(5)}`}
                mono
              />
              <Field label="Last Telemetry Ping" value={formatTimestamp(selectedBus.timestamp)} />
            </div>
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
