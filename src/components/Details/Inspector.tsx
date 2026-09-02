import type { RoadSegment } from '../../types/roadSegments';
import type { Event } from '../../types/events';
import type { Incident } from '../../types/incidents';
import type { GpsRecord } from '../../types/gps';
import { getRoadColor, getRoadStatusLabel } from '../../utils/roadColor';
import { formatTimestamp, formatConfidence, getEventTypeLabel } from '../../utils/formatters';
import { ConditionHistory } from '../Analytics/ConditionHistory';
import { Camera, Image as ImageIcon, Database, CheckCircle, Code } from 'lucide-react';

interface InspectorProps {
  selectedRoad: RoadSegment | null;
  selectedEvent: Event | null;
  selectedIncident: Incident | null;
  selectedGpsRecord?: GpsRecord | null;
  segmentHistory: { date: string; score: number }[];
  onClose: () => void;
}

export function Inspector({
  selectedRoad,
  selectedEvent,
  selectedIncident,
  selectedGpsRecord,
  segmentHistory,
  onClose,
}: InspectorProps) {
  if (!selectedRoad && !selectedEvent && !selectedIncident && !selectedGpsRecord) {
    return (
      <div className="inspector-panel empty">
        <div className="flex flex-col items-center gap-2">
          <Database className="w-8 h-8 text-slate-600 mb-1" />
          <p className="inspector-placeholder">
            Select any GPS record or telemetry stream row to inspect its Supabase schema fields, coordinate precision, and JSON payload.
          </p>
        </div>
      </div>
    );
  }

  const typeLabel = selectedGpsRecord
    ? 'GPS Telemetry Record'
    : selectedRoad
    ? 'Road Segment'
    : selectedEvent
    ? 'Event'
    : 'Incident';

  const title = selectedGpsRecord
    ? `${selectedGpsRecord.bus_id} @ ${selectedGpsRecord.location || 'GPS Waypoint'}`
    : selectedRoad
    ? (selectedRoad.name || selectedRoad.segment_id)
    : selectedEvent
    ? (selectedEvent.class_name || getEventTypeLabel(selectedEvent.event_type))
    : selectedIncident!.incident_type;

  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

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
        {/* ─── GPS Telemetry Record (Primary) ─── */}
        {selectedGpsRecord && (
          <div className="inspector-section">
            <div className="inspector-score-card" style={{ borderColor: '#38bdf8' }}>
              <div className="score-label" style={{ color: '#38bdf8' }}>GPS Vehicle Telemetry</div>
              <div className="score-value text-sky-400" style={{ fontSize: '28px' }}>
                {selectedGpsRecord.speed.toFixed(1)} <span className="score-max text-slate-400">km/h</span>
              </div>
              <div
                className="score-status-pill"
                style={{
                  backgroundColor: 'rgba(56,189,248,0.15)',
                  borderColor: '#38bdf8',
                  color: '#38bdf8',
                }}
              >
                {selectedGpsRecord.bus_id}
              </div>
            </div>

            <div className="inspector-grid">
              <Field label="Record ID (UUID)" value={selectedGpsRecord.id || 'Pending Insert'} mono />
              <Field label="Vehicle / Bus ID" value={selectedGpsRecord.bus_id} mono />
              <Field label="Latitude (double precision)" value={selectedGpsRecord.latitude.toFixed(6)} mono />
              <Field label="Longitude (double precision)" value={selectedGpsRecord.longitude.toFixed(6)} mono />
              <Field label="Speed (double precision)" value={`${selectedGpsRecord.speed.toFixed(1)} km/h`} mono />
              <Field label="Heading (double precision)" value={`${selectedGpsRecord.heading ?? 0}°`} mono />
              <Field label="Location / Sector" value={selectedGpsRecord.location || 'Not Specified'} />
              <Field label="Timestamp (timestamptz)" value={selectedGpsRecord.timestamp} mono />
            </div>

            {/* Supabase Schema Alignment Card */}
            <div className="p-3 bg-slate-900 rounded-xl border border-slate-700/60">
              <div className="text-xs font-semibold text-sky-300 mb-2 flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                <span>Supabase Table Alignment (`public.gps_records`)</span>
              </div>
              <div className="text-[11px] text-slate-300 space-y-1">
                <div className="flex justify-between border-b border-slate-800 pb-1">
                  <span className="text-slate-400">latitude / longitude:</span>
                  <span className="font-mono text-sky-300">double precision</span>
                </div>
                <div className="flex justify-between border-b border-slate-800 pb-1">
                  <span className="text-slate-400">speed:</span>
                  <span className="font-mono text-sky-300">double precision</span>
                </div>
                <div className="flex justify-between border-b border-slate-800 pb-1">
                  <span className="text-slate-400">timestamp:</span>
                  <span className="font-mono text-sky-300">timestamptz</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">id:</span>
                  <span className="font-mono text-sky-300">uuid (primary key)</span>
                </div>
              </div>
            </div>

            {/* Raw JSON Payload */}
            <div className="p-3 bg-black/60 rounded-xl border border-slate-800">
              <div className="text-xs font-semibold text-slate-400 mb-1 flex items-center gap-1.5">
                <Code className="w-3.5 h-3.5 text-indigo-400" />
                <span>Raw Ingestion JSON Payload</span>
              </div>
              <pre className="text-[10px] font-mono text-slate-300 overflow-x-auto p-2 bg-slate-950 rounded border border-slate-800">
                {JSON.stringify(selectedGpsRecord, null, 2)}
              </pre>
            </div>
          </div>
        )}

        {/* ─── Road Segment ─── */}
        {selectedRoad && !selectedGpsRecord && (
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
        {selectedEvent && !selectedGpsRecord && (
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

            {selectedEvent.evidence_uri && (
              <div className="mt-4 p-3 bg-slate-900/80 rounded-xl border border-slate-800">
                <div className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
                  <Camera className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Keyframe Evidence Crop</span>
                </div>
                <img
                  src={selectedEvent.evidence_uri.startsWith('http') ? selectedEvent.evidence_uri : `${baseUrl}${selectedEvent.evidence_uri}`}
                  alt="Defect Evidence"
                  className="rounded-lg max-h-48 w-full object-cover border border-slate-700 shadow-inner"
                  onError={(e) => {
                    (e.target as HTMLElement).style.display = 'none';
                  }}
                />
              </div>
            )}
          </div>
        )}

        {/* ─── Incident ─── */}
        {selectedIncident && !selectedGpsRecord && (
          <div className="inspector-section">
            <div className="inspector-score-card">
              <div className="score-label">Incident Severity Score</div>
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

            {selectedIncident.evidence_uri && (
              <div className="mt-4 p-3 bg-slate-900/80 rounded-xl border border-slate-800">
                <div className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
                  <ImageIcon className="w-3.5 h-3.5 text-rose-400" />
                  <span>Incident Crop Evidence</span>
                </div>
                <img
                  src={selectedIncident.evidence_uri.startsWith('http') ? selectedIncident.evidence_uri : `${baseUrl}${selectedIncident.evidence_uri}`}
                  alt="Incident Evidence"
                  className="rounded-lg max-h-48 w-full object-cover border border-slate-700 shadow-inner"
                  onError={(e) => {
                    (e.target as HTMLElement).style.display = 'none';
                  }}
                />
              </div>
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
