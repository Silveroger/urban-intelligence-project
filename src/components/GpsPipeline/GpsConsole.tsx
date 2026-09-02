import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Play,
  Square,
  Send,
  UploadCloud,
  Database,
  CheckCircle2,
  AlertCircle,
  Clock,
  Radio,
  RefreshCw,
  PlusCircle,
  FileText,
  Activity,
  Server,
  Zap,
  Check,
  AlertTriangle
} from 'lucide-react';
import type { GpsRecord, TelemetryStreamItem, IngestionStats } from '../../types/gps';
import {
  insertGpsRecord,
  insertGpsBatch,
  fetchRecentGpsRecords,
  generateNextSimulatedGps,
  validateGpsRecord,
  parseGpsFile,
} from '../../services/gpsPipeline';
import { isSupabaseConfigured, testSupabaseConnection } from '../../services/supabase';

interface GpsConsoleProps {
  onSelectRecord?: (record: GpsRecord | null) => void;
  selectedRecord?: GpsRecord | null;
}

export function GpsConsole({ onSelectRecord, selectedRecord }: GpsConsoleProps) {
  // ─── Stream State ───
  const [streamItems, setStreamItems] = useState<TelemetryStreamItem[]>([]);
  const [isSimulating, setIsSimulating] = useState(false);
  const [streamIntervalMs, setStreamIntervalMs] = useState(2000);
  const [busId, setBusId] = useState('BUS-101');
  const simIndexRef = useRef(0);

  // ─── Verification & Database State ───
  const [supabaseRecords, setSupabaseRecords] = useState<GpsRecord[]>([]);
  const [isVerifying, setIsVerifying] = useState(false);
  const [activeTab, setActiveTab] = useState<'stream' | 'manual' | 'upload' | 'db_verify'>('stream');

  // ─── Connection & Stats ───
  const [connStatus, setConnStatus] = useState<{ connected: boolean; message: string; latencyMs?: number }>({
    connected: isSupabaseConfigured,
    message: isSupabaseConfigured ? 'Supabase connected' : 'Local Simulated Mode (Enter VITE_SUPABASE_URL in .env)',
  });
  const [stats, setStats] = useState<IngestionStats>({
    totalTransmitted: 0,
    totalSuccess: 0,
    totalErrors: 0,
    totalDuplicatesSkipped: 0,
    lastLatencyMs: 0,
    lastSyncTime: null,
  });

  // ─── Manual Form State ───
  const [manualLat, setManualLat] = useState('30.735200');
  const [manualLng, setManualLng] = useState('76.782100');
  const [manualSpeed, setManualSpeed] = useState('32.5');
  const [manualHeading, setManualHeading] = useState('90');
  const [manualLocation, setManualLocation] = useState('Sector 17 City Centre Plaza');
  const [manualError, setManualError] = useState<string | null>(null);
  const [manualSuccess, setManualSuccess] = useState<string | null>(null);

  // ─── File Upload State ───
  const [parsedFileRecords, setParsedFileRecords] = useState<GpsRecord[]>([]);
  const [uploadFileName, setUploadFileName] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [isBatchUploading, setIsBatchUploading] = useState(false);

  // Check connection on mount
  useEffect(() => {
    testSupabaseConnection().then(setConnStatus);
  }, []);

  // ─── Telemetry Dispatcher ───
  const transmitRecord = useCallback(async (record: GpsRecord) => {
    const item: TelemetryStreamItem = {
      record,
      status: 'transmitting',
    };

    setStreamItems((prev) => [item, ...prev.slice(0, 99)]);

    const res = await insertGpsRecord(record);

    const updatedRecord: GpsRecord = {
      ...record,
      id: res.data?.id || record.id || `rec_${Date.now()}`,
      created_at: res.data?.created_at || new Date().toISOString(),
    };

    setStats((prev) => ({
      totalTransmitted: prev.totalTransmitted + 1,
      totalSuccess: res.success ? prev.totalSuccess + 1 : prev.totalSuccess,
      totalErrors: !res.success ? prev.totalErrors + 1 : prev.totalErrors,
      totalDuplicatesSkipped: res.duplicateSkipped ? prev.totalDuplicatesSkipped + 1 : prev.totalDuplicatesSkipped,
      lastLatencyMs: res.latencyMs,
      lastSyncTime: new Date().toLocaleTimeString(),
    }));

    setStreamItems((prev) =>
      prev.map((it) =>
        it.record.timestamp === record.timestamp && it.record.bus_id === record.bus_id
          ? {
              record: updatedRecord,
              status: res.success ? (res.duplicateSkipped ? 'duplicate_skipped' : 'synced') : 'error',
              statusMessage: res.error,
              latencyMs: res.latencyMs,
              syncedAt: new Date().toLocaleTimeString(),
            }
          : it
      )
    );

    return res;
  }, []);

  // ─── Simulator Loop ───
  useEffect(() => {
    if (!isSimulating) return;

    const timer = setInterval(async () => {
      const { record, nextIndex } = generateNextSimulatedGps(busId, simIndexRef.current);
      simIndexRef.current = nextIndex;
      await transmitRecord(record);
    }, streamIntervalMs);

    return () => clearInterval(timer);
  }, [isSimulating, streamIntervalMs, busId, transmitRecord]);

  // ─── Manual Form Submission ───
  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setManualError(null);
    setManualSuccess(null);

    const lat = parseFloat(manualLat);
    const lng = parseFloat(manualLng);
    const spd = parseFloat(manualSpeed);
    const hdg = parseFloat(manualHeading);

    const candidate: GpsRecord = {
      bus_id: busId,
      timestamp: new Date().toISOString(),
      latitude: lat,
      longitude: lng,
      speed: isNaN(spd) ? 0 : spd,
      heading: isNaN(hdg) ? 0 : hdg,
      location: manualLocation.trim() || undefined,
    };

    const val = validateGpsRecord(candidate);
    if (!val.valid) {
      setManualError(val.errors.join(' '));
      return;
    }

    const res = await transmitRecord(candidate);
    if (res.success) {
      setManualSuccess(`GPS Record successfully transmitted and stored (Latency: ${res.latencyMs}ms)!`);
    } else {
      setManualError(res.error || 'Failed to insert GPS record into Supabase.');
    }
  };

  // ─── File Upload Handler ───
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadFileName(file.name);
    setUploadStatus('Parsing GPS log file...');
    try {
      const records = await parseGpsFile(file, busId);
      setParsedFileRecords(records);
      setUploadStatus(`Parsed ${records.length} valid GPS coordinates from "${file.name}". Ready for batch insertion.`);
    } catch (err: unknown) {
      setParsedFileRecords([]);
      const errMsg = err instanceof Error ? err.message : 'Unknown parsing error';
      setUploadStatus(`Error parsing file: ${errMsg}`);
    }
  };

  const handleBatchInsert = async () => {
    if (parsedFileRecords.length === 0) return;
    setIsBatchUploading(true);
    setUploadStatus(`Transmitting ${parsedFileRecords.length} records to Supabase...`);
    const res = await insertGpsBatch(parsedFileRecords);
    setIsBatchUploading(false);

    setStats((prev) => ({
      ...prev,
      totalTransmitted: prev.totalTransmitted + res.total,
      totalSuccess: prev.totalSuccess + res.successCount,
      totalErrors: prev.totalErrors + res.errorCount,
      lastSyncTime: new Date().toLocaleTimeString(),
    }));

    // Prepend to stream items
    const streamBatch: TelemetryStreamItem[] = parsedFileRecords.slice(0, 30).map((r) => ({
      record: r,
      status: res.errorCount === 0 ? 'synced' : 'error',
      syncedAt: new Date().toLocaleTimeString(),
    }));
    setStreamItems((prev) => [...streamBatch, ...prev].slice(0, 100));

    if (res.errorCount === 0) {
      setUploadStatus(`Batch complete! Successfully stored all ${res.successCount} GPS records in Supabase.`);
    } else {
      setUploadStatus(`Batch finished with issues: ${res.successCount} succeeded, ${res.errorCount} failed. ${res.errors.slice(0, 2).join(' ')}`);
    }
  };

  // ─── Query Supabase Verifier ───
  const handleVerifySupabase = async () => {
    setIsVerifying(true);
    const recs = await fetchRecentGpsRecords(30);
    setSupabaseRecords(recs);
    setIsVerifying(false);
  };

  const handleTabChange = (tab: 'stream' | 'manual' | 'upload' | 'db_verify') => {
    setActiveTab(tab);
    if (tab === 'db_verify') {
      handleVerifySupabase();
    }
  };

  return (
    <div className="gps-console-wrapper">
      {/* ── Top Pipeline Control Strip ── */}
      <div className="pipeline-header-bar">
        <div className="pipeline-status-group">
          <div className="status-indicator">
            <span className={`status-pill ${connStatus.connected ? 'connected' : 'warning'}`}>
              <Server className="w-3.5 h-3.5" />
              <span>{connStatus.connected ? 'Supabase Active' : 'Simulated Pipeline'}</span>
            </span>
          </div>

          <div className="vehicle-selector">
            <label>Vehicle Sensing Node:</label>
            <select value={busId} onChange={(e) => setBusId(e.target.value)} className="console-select">
              <option value="BUS-101">BUS-101 (Chandigarh Sector Line)</option>
              <option value="BUS-204">BUS-204 (Madhya Marg Express)</option>
              <option value="BUS-308">BUS-308 (Heritage Corridor)</option>
              <option value="TEST-RIG-01">TEST-RIG-01 (Hardware Diagnostic Unit)</option>
            </select>
          </div>
        </div>

        {/* Live Simulator Controls */}
        <div className="pipeline-controls">
          <div className="stream-rate-selector">
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={streamIntervalMs}
              onChange={(e) => setStreamIntervalMs(Number(e.target.value))}
              disabled={isSimulating}
              className="console-select small"
            >
              <option value={1000}>1.0s (1 Hz Stream)</option>
              <option value={2000}>2.0s (0.5 Hz Stream)</option>
              <option value={3000}>3.0s (Standard)</option>
              <option value={5000}>5.0s (Battery Saver)</option>
            </select>
          </div>

          <button
            type="button"
            onClick={() => setIsSimulating((v) => !v)}
            className={`btn-stream-toggle ${isSimulating ? 'btn-stop' : 'btn-start'}`}
          >
            {isSimulating ? (
              <>
                <Square className="w-4 h-4 fill-current" />
                <span>Stop GPS Stream</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Start GPS Stream</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={async () => {
              const { record, nextIndex } = generateNextSimulatedGps(busId, simIndexRef.current);
              simIndexRef.current = nextIndex;
              await transmitRecord(record);
            }}
            disabled={isSimulating}
            className="btn-single-step"
            title="Transmit 1 discrete GPS coordinate"
          >
            <Zap className="w-3.5 h-3.5" />
            <span>Emit 1 Ping</span>
          </button>
        </div>
      </div>

      {/* ── KPI & Health Cards ── */}
      <div className="pipeline-kpi-grid">
        <div className="metric-box">
          <div className="metric-label">
            <Radio className="w-3.5 h-3.5 text-sky-400" />
            <span>Transmitted GPS Points</span>
          </div>
          <div className="metric-value text-sky-400">{stats.totalTransmitted}</div>
          <div className="metric-sub">Session coordinates collected</div>
        </div>

        <div className="metric-box">
          <div className="metric-label">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Supabase Sync Rate</span>
          </div>
          <div className="metric-value text-emerald-400">
            {stats.totalTransmitted > 0
              ? `${Math.round((stats.totalSuccess / stats.totalTransmitted) * 100)}%`
              : '100%'}
          </div>
          <div className="metric-sub">{stats.totalSuccess} stored in Supabase</div>
        </div>

        <div className="metric-box">
          <div className="metric-label">
            <Activity className="w-3.5 h-3.5 text-indigo-400" />
            <span>Insert Latency</span>
          </div>
          <div className="metric-value text-indigo-400">{stats.lastLatencyMs} ms</div>
          <div className="metric-sub">Round-trip database write</div>
        </div>

        <div className="metric-box">
          <div className="metric-label">
            <Database className="w-3.5 h-3.5 text-amber-400" />
            <span>Duplicate Protection</span>
          </div>
          <div className="metric-value text-amber-400">{stats.totalDuplicatesSkipped}</div>
          <div className="metric-sub">Redundant coordinates skipped</div>
        </div>
      </div>

      {/* ── Navigation Tabs ── */}
      <div className="console-tab-bar">
        <button
          type="button"
          className={`console-tab ${activeTab === 'stream' ? 'active' : ''}`}
          onClick={() => handleTabChange('stream')}
        >
          <Radio className="w-4 h-4" />
          <span>Live Telemetry Stream ({streamItems.length})</span>
        </button>
        <button
          type="button"
          className={`console-tab ${activeTab === 'manual' ? 'active' : ''}`}
          onClick={() => handleTabChange('manual')}
        >
          <PlusCircle className="w-4 h-4" />
          <span>Manual Coordinate Ingestion</span>
        </button>
        <button
          type="button"
          className={`console-tab ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => handleTabChange('upload')}
        >
          <UploadCloud className="w-4 h-4" />
          <span>Batch GPS File Ingestion (.json / .csv)</span>
        </button>
        <button
          type="button"
          className={`console-tab ${activeTab === 'db_verify' ? 'active' : ''}`}
          onClick={() => handleTabChange('db_verify')}
        >
          <Database className="w-4 h-4" />
          <span>Supabase Table Verifier (Live Query)</span>
        </button>
      </div>

      {/* ── Tab Content ── */}
      <div className="console-body">
        {/* TAB 1: Live Telemetry Stream */}
        {activeTab === 'stream' && (
          <div className="stream-container">
            <div className="table-responsive">
              <table className="telemetry-table">
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>Bus ID</th>
                    <th>Timestamp (UTC)</th>
                    <th>Latitude (°N)</th>
                    <th>Longitude (°E)</th>
                    <th>Speed (km/h)</th>
                    <th>Heading</th>
                    <th>Location / Sector</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {streamItems.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="empty-row">
                        <div className="empty-state">
                          <Radio className="w-8 h-8 text-slate-500 mb-2 animate-pulse" />
                          <p>No GPS telemetry stream active.</p>
                          <span className="text-xs text-slate-500">
                            Click <strong>"Start GPS Stream"</strong> or <strong>"Emit 1 Ping"</strong> above to collect and transmit GPS coordinates to Supabase.
                          </span>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    streamItems.map((item, idx) => {
                      const isSelected = selectedRecord?.timestamp === item.record.timestamp;
                      return (
                        <tr
                          key={`${item.record.bus_id}_${item.record.timestamp}_${idx}`}
                          className={`stream-row ${isSelected ? 'row-selected' : ''}`}
                          onClick={() => onSelectRecord?.(item.record)}
                        >
                          <td>
                            {item.status === 'transmitting' && (
                              <span className="badge-status badge-transmitting">
                                <RefreshCw className="w-3 h-3 animate-spin" />
                                <span>SENDING</span>
                              </span>
                            )}
                            {item.status === 'synced' && (
                              <span className="badge-status badge-synced">
                                <Check className="w-3 h-3" />
                                <span>SYNCED</span>
                              </span>
                            )}
                            {item.status === 'duplicate_skipped' && (
                              <span className="badge-status badge-skipped" title={item.statusMessage}>
                                <span>SKIPPED</span>
                              </span>
                            )}
                            {item.status === 'error' && (
                              <span className="badge-status badge-error" title={item.statusMessage}>
                                <AlertCircle className="w-3 h-3" />
                                <span>ERROR</span>
                              </span>
                            )}
                          </td>
                          <td className="font-mono font-semibold text-slate-200">{item.record.bus_id}</td>
                          <td className="font-mono text-xs text-slate-400">
                            {new Date(item.record.timestamp).toLocaleTimeString()}
                          </td>
                          <td className="font-mono text-sky-300 font-semibold">{item.record.latitude.toFixed(6)}</td>
                          <td className="font-mono text-sky-300 font-semibold">{item.record.longitude.toFixed(6)}</td>
                          <td className="font-mono font-medium text-slate-200">{item.record.speed.toFixed(1)}</td>
                          <td className="font-mono text-xs text-slate-400">{item.record.heading ?? 0}°</td>
                          <td className="text-xs text-slate-300">{item.record.location || '—'}</td>
                          <td>
                            <button
                              type="button"
                              className="btn-inspect-small"
                              onClick={(e) => {
                                e.stopPropagation();
                                onSelectRecord?.(item.record);
                              }}
                            >
                              Inspect
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 2: Manual GPS Ingestion Form */}
        {activeTab === 'manual' && (
          <div className="panel-tab-body">
            <div className="form-card">
              <div className="form-card-header">
                <PlusCircle className="w-5 h-5 text-indigo-400" />
                <div>
                  <h3 className="text-sm font-bold text-white">Manual GPS Coordinate Ingestion</h3>
                  <p className="text-xs text-slate-400">
                    Directly inject discrete GPS coordinate packets to validate Supabase table insertion.
                  </p>
                </div>
              </div>

              {manualSuccess && (
                <div className="alert-box alert-success">
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                  <span>{manualSuccess}</span>
                </div>
              )}

              {manualError && (
                <div className="alert-box alert-error">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{manualError}</span>
                </div>
              )}

              <form onSubmit={handleManualSubmit} className="grid-form">
                <div className="form-group">
                  <label>Latitude (°N) [double precision]</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={manualLat}
                    onChange={(e) => setManualLat(e.target.value)}
                    className="console-input"
                    placeholder="e.g. 30.735200"
                  />
                  <span className="field-hint">Range: -90.000000 to +90.000000</span>
                </div>

                <div className="form-group">
                  <label>Longitude (°E) [double precision]</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={manualLng}
                    onChange={(e) => setManualLng(e.target.value)}
                    className="console-input"
                    placeholder="e.g. 76.782100"
                  />
                  <span className="field-hint">Range: -180.000000 to +180.000000</span>
                </div>

                <div className="form-group">
                  <label>Speed (km/h) [double precision]</label>
                  <input
                    type="number"
                    step="any"
                    value={manualSpeed}
                    onChange={(e) => setManualSpeed(e.target.value)}
                    className="console-input"
                    placeholder="35.0"
                  />
                  <span className="field-hint">Non-negative velocity</span>
                </div>

                <div className="form-group">
                  <label>Heading (Degrees) [double precision]</label>
                  <input
                    type="number"
                    step="any"
                    value={manualHeading}
                    onChange={(e) => setManualHeading(e.target.value)}
                    className="console-input"
                    placeholder="90"
                  />
                  <span className="field-hint">Compass bearing 0° to 360°</span>
                </div>

                <div className="form-group span-2">
                  <label>Location / Sector Name (Text)</label>
                  <input
                    type="text"
                    value={manualLocation}
                    onChange={(e) => setManualLocation(e.target.value)}
                    className="console-input"
                    placeholder="e.g. Sector 17, Chandigarh / Madhya Marg"
                  />
                  <span className="field-hint">Assigned urban sector for backend zone analytics</span>
                </div>

                <div className="form-actions span-2">
                  <button type="submit" className="btn-primary">
                    <Send className="w-4 h-4" />
                    <span>Send GPS Record to Supabase</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* TAB 3: Batch GPS File Upload */}
        {activeTab === 'upload' && (
          <div className="panel-tab-body">
            <div className="form-card">
              <div className="form-card-header">
                <UploadCloud className="w-5 h-5 text-sky-400" />
                <div>
                  <h3 className="text-sm font-bold text-white">Batch GPS File Ingestion</h3>
                  <p className="text-xs text-slate-400">
                    Upload telemetry tracks from GPS loggers (.json, .csv) to batch insert into Supabase.
                  </p>
                </div>
              </div>

              <div className="upload-dropzone">
                <FileText className="w-10 h-10 text-slate-500 mb-2" />
                <label className="btn-browse-file">
                  <span>Browse GPS Log File</span>
                  <input
                    type="file"
                    accept=".json,.csv,.txt"
                    onChange={handleFileUpload}
                    style={{ display: 'none' }}
                  />
                </label>
                <p className="text-xs text-slate-400 mt-2">
                  Supported formats: <strong>.json</strong> (array of coordinate objects) or <strong>.csv</strong> (columns: latitude, longitude, speed, location)
                </p>
              </div>

              {uploadStatus && (
                <div className="alert-box alert-info">
                  <Activity className="w-4 h-4 flex-shrink-0" />
                  <span>{uploadStatus}</span>
                </div>
              )}

              {parsedFileRecords.length > 0 && (
                <div className="parsed-preview-box">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-bold uppercase text-slate-300">
                      Preview of {parsedFileRecords.length} GPS coordinates from {uploadFileName}
                    </span>
                    <button
                      type="button"
                      disabled={isBatchUploading}
                      onClick={handleBatchInsert}
                      className="btn-primary small"
                    >
                      {isBatchUploading ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          <span>Inserting to Supabase...</span>
                        </>
                      ) : (
                        <>
                          <UploadCloud className="w-3.5 h-3.5" />
                          <span>Insert All {parsedFileRecords.length} Points to Supabase</span>
                        </>
                      )}
                    </button>
                  </div>

                  <div className="table-preview-scroll">
                    <table className="telemetry-table preview-table">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th>Bus ID</th>
                          <th>Latitude</th>
                          <th>Longitude</th>
                          <th>Speed</th>
                          <th>Heading</th>
                          <th>Location</th>
                        </tr>
                      </thead>
                      <tbody>
                        {parsedFileRecords.slice(0, 10).map((r, i) => (
                          <tr key={i}>
                            <td className="font-mono text-slate-400">{i + 1}</td>
                            <td className="font-mono">{r.bus_id}</td>
                            <td className="font-mono text-sky-300">{r.latitude.toFixed(6)}</td>
                            <td className="font-mono text-sky-300">{r.longitude.toFixed(6)}</td>
                            <td className="font-mono">{r.speed} km/h</td>
                            <td className="font-mono">{r.heading ?? 0}°</td>
                            <td>{r.location || '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {parsedFileRecords.length > 10 && (
                    <div className="text-xs text-slate-500 mt-2 text-center">
                      + {parsedFileRecords.length - 10} more records in file
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 4: Supabase Database Direct Verifier */}
        {activeTab === 'db_verify' && (
          <div className="panel-tab-body">
            <div className="form-card">
              <div className="form-card-header justify-between">
                <div className="flex items-center gap-3">
                  <Database className="w-5 h-5 text-emerald-400" />
                  <div>
                    <h3 className="text-sm font-bold text-white">Supabase Live Records Verifier</h3>
                    <p className="text-xs text-slate-400">
                      Query stored rows directly from the Supabase <code className="text-sky-300">public.gps_records</code> table.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleVerifySupabase}
                  disabled={isVerifying}
                  className="btn-refresh"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isVerifying ? 'animate-spin' : ''}`} />
                  <span>Refresh Supabase Query</span>
                </button>
              </div>

              {!isSupabaseConfigured && (
                <div className="alert-box alert-warning">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0 text-amber-400" />
                  <div>
                    <strong>Supabase not yet configured in .env:</strong>
                    <p className="text-xs mt-1">
                      Set <code className="text-amber-200">VITE_SUPABASE_URL</code> and <code className="text-amber-200">VITE_SUPABASE_ANON_KEY</code> to enable live database verification.
                    </p>
                  </div>
                </div>
              )}

              <div className="table-responsive">
                <table className="telemetry-table">
                  <thead>
                    <tr>
                      <th>Record ID (UUID)</th>
                      <th>Bus ID</th>
                      <th>Recorded At (timestamptz)</th>
                      <th>Latitude (°N)</th>
                      <th>Longitude (°E)</th>
                      <th>Speed (km/h)</th>
                      <th>Location / Sector</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {supabaseRecords.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="empty-row">
                          <div className="empty-state">
                            <Database className="w-8 h-8 text-slate-500 mb-2" />
                            <p>No records returned from Supabase.</p>
                            <span className="text-xs text-slate-500">
                              Either the table is empty or environment credentials need configuration.
                            </span>
                          </div>
                        </td>
                      </tr>
                    ) : (
                      supabaseRecords.map((r, i) => (
                        <tr
                          key={r.id || i}
                          className="stream-row"
                          onClick={() => onSelectRecord?.(r)}
                        >
                          <td className="font-mono text-xs text-sky-400">{r.id?.slice(0, 8)}...</td>
                          <td className="font-mono font-semibold text-slate-200">{r.bus_id}</td>
                          <td className="font-mono text-xs text-slate-400">
                            {r.timestamp ? new Date(r.timestamp).toISOString() : '—'}
                          </td>
                          <td className="font-mono text-sky-300 font-semibold">{r.latitude.toFixed(6)}</td>
                          <td className="font-mono text-sky-300 font-semibold">{r.longitude.toFixed(6)}</td>
                          <td className="font-mono">{r.speed.toFixed(1)}</td>
                          <td className="text-xs text-slate-300">{r.location || '—'}</td>
                          <td>
                            <button
                              type="button"
                              className="btn-inspect-small"
                              onClick={(e) => {
                                e.stopPropagation();
                                onSelectRecord?.(r);
                              }}
                            >
                              Inspect
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
