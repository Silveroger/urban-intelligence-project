import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import axios from 'axios';
import { Play, CheckCircle2, AlertTriangle, Cpu, RefreshCw, X, Eye, MonitorPlay, Target, ShieldCheck } from 'lucide-react';
import type { Event } from '../../types/events';
import type { Incident } from '../../types/incidents';
import type { FilterState } from '../../types/filters';

interface VideoProcessingHubProps {
  isOpen: boolean;
  onClose: () => void;
  filters: FilterState;
  onNewEvent?: (event: Event) => void;
  onNewIncident?: (incident: Incident) => void;
}

interface DetectionLogEntry {
  id: string;
  type: string;
  class_name: string;
  conf: number;
  severity: number;
  time: string;
  risk_score?: number;
  risk_level?: string;
  breadth_cm?: number;
  depth_cm?: number;
}

interface PipelineEventPayload {
  event_id: string;
  bus_id?: string;
  timestamp?: string;
  latitude: number;
  longitude: number;
  road_segment_id?: string;
  event_type: 'road_defect' | 'waterlogging' | 'traffic' | 'incident' | 'infrastructure' | 'pedestrian';
  class_name: string;
  confidence: number;
  severity?: number;
  evidence_uri?: string;
  risk_score?: number;
  risk_level?: string;
  breadth_cm?: number;
  depth_cm?: number;
  dimensions?: { breadth_cm: number; depth_cm: number; area_sq_cm?: number; bbox_width?: number; bbox_height?: number };
  risk_assessment?: string;
}

interface VideoStatusResponse {
  is_running: boolean;
  progress: number;
  current_frame: number;
  total_frames: number;
  status_message: string;
  last_result?: {
    total_frames_analyzed?: number;
    total_events_detected?: number;
    total_incidents_flagged?: number;
    events?: PipelineEventPayload[];
  } | null;
}

const DETECTOR_LABELS: Record<string, string> = {
  road_defect: 'Road Defects (Potholes, Cracks, Dividers)',
  waterlogging: 'Waterlogging & Puddles',
  traffic: 'Traffic Density & Pedestrians',
  incident: 'Incidents (Rash Driving, Plate OCR)',
};

export function VideoProcessingHub({
  isOpen,
  onClose,
  filters,
  onNewEvent,
  onNewIncident,
}: VideoProcessingHubProps) {
  const [busId, setBusId] = useState('BUS-101');
  const [useSample, setUseSample] = useState(true);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [gpsFile, setGpsFile] = useState<File | null>(null);
  const [showLaptopWindow, setShowLaptopWindow] = useState(true);
  const [videoPreviewUrl, setVideoPreviewUrl] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('Ready for inference');
  const [detectedLog, setDetectedLog] = useState<DetectionLogEntry[]>([]);
  const [modelAccuracy, setModelAccuracy] = useState<{ total: number; avgConf: number; byClass: Record<string, { count: number; avgConf: number }> }>({
    total: 0,
    avgConf: 0,
    byClass: {},
  });

  const videoRef = useRef<HTMLVideoElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const onNewEventRef = useRef(onNewEvent);
  onNewEventRef.current = onNewEvent;

  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  const handleVideoFileChange = (file: File | null) => {
    setVideoFile(file);
    if (videoPreviewUrl) {
      URL.revokeObjectURL(videoPreviewUrl);
    }
    if (file) {
      setVideoPreviewUrl(URL.createObjectURL(file));
    } else {
      setVideoPreviewUrl(null);
    }
  };

  // Poll status when processing is active
  useEffect(() => {
    if (!isProcessing) return;

    const interval = setInterval(async () => {
      try {
        const { data } = await axios.get<VideoStatusResponse>(`${baseUrl}/api/v1/ingest/video/status`);
        setProgress(data.progress || 0);
        setStatusMessage(data.status_message || 'Analyzing frames...');

        if (!data.is_running && data.progress >= 99) {
          setIsProcessing(false);
          setStatusMessage('Processing completed successfully!');
          setProgress(100);
          if (data.last_result?.events) {
            const mapped: DetectionLogEntry[] = data.last_result.events.map((e) => ({
              id: e.event_id,
              type: e.event_type,
              class_name: e.class_name || e.event_type,
              conf: e.confidence,
              severity: e.severity ?? 1,
              time: new Date().toLocaleTimeString(),
              risk_score: e.risk_score,
              risk_level: e.risk_level,
              breadth_cm: e.breadth_cm,
              depth_cm: e.depth_cm,
            }));
            setDetectedLog(mapped);
            updateModelAccuracy(mapped);

            // Push all detected events to the GIS map
            if (onNewEventRef.current) {
              data.last_result.events.forEach((evt) => {
                onNewEventRef.current?.({
                  event_id: evt.event_id,
                  bus_id: evt.bus_id || busId,
                  timestamp: evt.timestamp || new Date().toISOString(),
                  latitude: evt.latitude,
                  longitude: evt.longitude,
                  road_segment_id: evt.road_segment_id || 'seg_detected',
                  event_type: evt.event_type || 'road_defect',
                  class_name: evt.class_name,
                  confidence: evt.confidence,
                  severity: evt.severity,
                  evidence_uri: evt.evidence_uri,
                  risk_score: evt.risk_score,
                  risk_level: evt.risk_level,
                  breadth_cm: evt.breadth_cm,
                  depth_cm: evt.depth_cm,
                  dimensions: evt.dimensions,
                  risk_assessment: evt.risk_assessment,
                });
              });
            }
          }
        }
      } catch {
        setProgress((prev) => {
          if (prev >= 100) {
            setIsProcessing(false);
            setStatusMessage('Simulated edge analysis complete!');
            return 100;
          }
          return prev + 12;
        });
      }
    }, 800);

    return () => clearInterval(interval);
  }, [isProcessing, baseUrl, busId]);

  // Compute model accuracy stats from detection log
  function updateModelAccuracy(entries: DetectionLogEntry[]) {
    if (entries.length === 0) return;
    const byClass: Record<string, { count: number; totalConf: number }> = {};
    let totalConf = 0;
    for (const e of entries) {
      totalConf += e.conf;
      if (!byClass[e.class_name]) {
        byClass[e.class_name] = { count: 0, totalConf: 0 };
      }
      byClass[e.class_name].count += 1;
      byClass[e.class_name].totalConf += e.conf;
    }
    const formatted: Record<string, { count: number; avgConf: number }> = {};
    for (const [cls, stats] of Object.entries(byClass)) {
      formatted[cls] = { count: stats.count, avgConf: stats.totalConf / stats.count };
    }
    setModelAccuracy({
      total: entries.length,
      avgConf: totalConf / entries.length,
      byClass: formatted,
    });
  }

  if (!isOpen) return null;

  const handleStartProcessing = async () => {
    setIsProcessing(true);
    setProgress(0);
    setStatusMessage('Initializing YOLO & OpenCV Edge Pipeline...');
    setDetectedLog([]);
    setModelAccuracy({ total: 0, avgConf: 0, byClass: {} });

    if (videoRef.current) {
      videoRef.current.play().catch(() => {});
    }

    const formData = new FormData();
    formData.append('bus_id', busId);
    formData.append('use_sample', String(useSample));
    formData.append('show_window', String(showLaptopWindow));
    // Send sidebar filter state as enabled_detectors JSON
    formData.append('enabled_detectors', JSON.stringify({
      road_defect: filters.eventTypes.road_defect,
      waterlogging: filters.eventTypes.waterlogging,
      traffic: filters.eventTypes.traffic,
      incident: filters.eventTypes.incident,
      pedestrian: filters.eventTypes.pedestrian ?? true,
    }));
    if (videoFile) formData.append('video_file', videoFile);
    if (gpsFile) formData.append('gps_file', gpsFile);

    try {
      await axios.post(`${baseUrl}/api/v1/ingest/video/process`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    } catch {
      // Offline fallback: simulate progressive events
      setTimeout(() => {
        const simEvt: Event = {
          event_id: `evt_sim_${Date.now()}`,
          bus_id: busId,
          timestamp: new Date().toISOString(),
          latitude: 30.7350,
          longitude: 76.7820,
          road_segment_id: 'seg_chandigarh_001',
          event_type: 'road_defect',
          class_name: 'pothole',
          confidence: 0.92,
          severity: 3,
        };
        onNewEvent?.(simEvt);
        const entry: DetectionLogEntry = {
          id: simEvt.event_id, type: 'road_defect', class_name: 'pothole',
          conf: 0.92, severity: 3, time: new Date().toLocaleTimeString(),
        };
        setDetectedLog((prev) => {
          const next = [entry, ...prev];
          updateModelAccuracy(next);
          return next;
        });
      }, 2500);

      setTimeout(() => {
        const simInc: Incident = {
          incident_id: `inc_sim_${Date.now()}`,
          timestamp: new Date().toISOString(),
          latitude: 30.7380,
          longitude: 76.7850,
          incident_type: 'rash_driving',
          incident_score: 0.95,
          vehicle_track_id: 'trk_102',
          plate_text: 'CH01AB1234',
          plate_confidence: 0.94,
          road_segment_id: 'seg_chandigarh_002',
        };
        onNewIncident?.(simInc);
        const entry: DetectionLogEntry = {
          id: simInc.incident_id, type: 'incident', class_name: 'rash_driving',
          conf: 0.94, severity: 4, time: new Date().toLocaleTimeString(),
        };
        setDetectedLog((prev) => {
          const next = [entry, ...prev];
          updateModelAccuracy(next);
          return next;
        });
      }, 4500);
    }
  };

  // Severity badge color
  function sevColor(s: number): string {
    if (s >= 4) return 'bg-red-500/20 text-red-400';
    if (s >= 3) return 'bg-orange-500/20 text-orange-400';
    if (s >= 2) return 'bg-amber-500/20 text-amber-400';
    return 'bg-slate-600/20 text-slate-400';
  }

  // Use createPortal to render outside the overflow:hidden parent
  return createPortal(
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        background: 'rgba(0,0,0,0.82)',
        backdropFilter: 'blur(6px)',
        overflowY: 'auto',
        padding: '24px 16px',
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        style={{
          background: '#0f172a',
          border: '1px solid #334155',
          borderRadius: '16px',
          maxWidth: '720px',
          width: '100%',
          color: '#e2e8f0',
          margin: 'auto 0',
          boxShadow: '0 25px 60px rgba(0,0,0,0.6)',
        }}
      >
        {/* ── Header ── */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '16px 24px', borderBottom: '1px solid #1e293b',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ padding: '8px', background: 'rgba(99,102,241,0.15)', borderRadius: '8px', color: '#818cf8' }}>
              <Cpu style={{ width: 20, height: 20 }} />
            </div>
            <div>
              <h2 style={{ fontSize: '15px', fontWeight: 700, color: '#fff', margin: 0 }}>
                Edge AI Video & Hardware Ingestion Hub
              </h2>
              <p style={{ fontSize: '11px', color: '#94a3b8', margin: '2px 0 0' }}>
                Process bus camera feeds with synchronized GPS & YOLO / OpenCV perception
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'transparent', border: 'none', color: '#94a3b8',
              cursor: 'pointer', padding: '6px', borderRadius: '6px',
            }}
            aria-label="Close"
          >
            <X style={{ width: 20, height: 20 }} />
          </button>
        </div>

        {/* ── Body ── */}
        <div ref={scrollRef} style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>

          {/* Config Row */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '11px', fontWeight: 600, color: '#cbd5e1' }}>Fleet Bus Identifier</label>
              <input
                type="text"
                value={busId}
                onChange={(e) => setBusId(e.target.value)}
                style={{
                  background: '#1e293b', border: '1px solid #334155', borderRadius: '8px',
                  padding: '8px 12px', fontSize: '13px', color: '#fff', outline: 'none',
                }}
                placeholder="e.g. BUS-101"
              />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '11px', fontWeight: 600, color: '#cbd5e1' }}>Feed Source Mode</label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button type="button" onClick={() => setUseSample(true)}
                  style={{
                    flex: 1, padding: '8px', borderRadius: '8px', fontSize: '11px', fontWeight: 600,
                    border: `1px solid ${useSample ? '#6366f1' : '#334155'}`,
                    background: useSample ? '#4f46e5' : '#1e293b',
                    color: useSample ? '#fff' : '#94a3b8', cursor: 'pointer',
                  }}>
                  Sample Preset
                </button>
                <button type="button" onClick={() => setUseSample(false)}
                  style={{
                    flex: 1, padding: '8px', borderRadius: '8px', fontSize: '11px', fontWeight: 600,
                    border: `1px solid ${!useSample ? '#6366f1' : '#334155'}`,
                    background: !useSample ? '#4f46e5' : '#1e293b',
                    color: !useSample ? '#fff' : '#94a3b8', cursor: 'pointer',
                  }}>
                  Upload Video & GPS
                </button>
              </div>
            </div>
          </div>

          {/* File Uploads */}
          {!useSample && (
            <div style={{
              display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px',
              padding: '14px', background: '#1e293b80', borderRadius: '12px',
              border: '1px solid #334155',
            }}>
              <div>
                <label style={{ fontSize: '11px', fontWeight: 500, color: '#cbd5e1', display: 'block', marginBottom: '6px' }}>
                  Hardware Video Stream (.mp4, .avi, .mkv, .mov, .h264, .ts, .mjpeg, .raw)
                </label>
                <input type="file" accept="video/*,.h264,.h265,.ts,.mjpeg,.raw,.mkv,.mov,.flv,.webm"
                  onChange={(e) => handleVideoFileChange(e.target.files?.[0] || null)}
                  style={{ fontSize: '11px', color: '#cbd5e1', cursor: 'pointer' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '11px', fontWeight: 500, color: '#cbd5e1', display: 'block', marginBottom: '6px' }}>
                  GPS Log (.csv, .json, .gpx, .nmea)
                </label>
                <input type="file" accept=".csv,.json,.gpx,.nmea,.txt"
                  onChange={(e) => setGpsFile(e.target.files?.[0] || null)}
                  style={{ fontSize: '11px', color: '#cbd5e1', cursor: 'pointer' }}
                />
              </div>
            </div>
          )}

          {/* Video Preview */}
          {videoPreviewUrl && (
            <div style={{ background: '#000', borderRadius: '12px', overflow: 'hidden', border: '1px solid #1e293b' }}>
              <div style={{
                fontSize: '11px', fontWeight: 600, color: '#94a3b8',
                padding: '6px 12px', background: '#0f172aee', display: 'flex',
                alignItems: 'center', gap: '6px', borderBottom: '1px solid #1e293b',
              }}>
                <Eye style={{ width: 14, height: 14, color: '#818cf8' }} />
                <span>Selected Video Preview</span>
              </div>
              <video ref={videoRef} src={videoPreviewUrl} controls
                style={{ width: '100%', maxHeight: '220px', objectFit: 'contain', background: '#000' }}
              />
            </div>
          )}

          {/* OpenCV Window Toggle */}
          <label style={{
            display: 'flex', alignItems: 'center', gap: '10px', padding: '12px',
            background: 'rgba(49,46,129,0.25)', border: '1px solid rgba(99,102,241,0.3)',
            borderRadius: '12px', cursor: 'pointer', userSelect: 'none',
          }}>
            <input type="checkbox" checked={showLaptopWindow}
              onChange={(e) => setShowLaptopWindow(e.target.checked)}
              style={{ width: '16px', height: '16px', cursor: 'pointer' }}
            />
            <MonitorPlay style={{ width: 16, height: 16, color: '#818cf8', flexShrink: 0 }} />
            <span style={{ fontSize: '12px', fontWeight: 500, color: '#e2e8f0' }}>
              Open <strong>Live OpenCV Scanning Window</strong> on laptop screen with bounding boxes & HUD
            </span>
          </label>

          {/* Active Detector Categories — synced with sidebar filters */}
          <div style={{
            background: '#020617cc', borderRadius: '12px', padding: '14px 16px',
            border: '1px solid #1e293b',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px' }}>
              <ShieldCheck style={{ width: 14, height: 14, color: '#34d399' }} />
              <span style={{ fontSize: '11px', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Active Detectors (synced with sidebar filters)
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {Object.entries(DETECTOR_LABELS).map(([key, label]) => {
                const isOn = filters.eventTypes[key as keyof typeof filters.eventTypes];
                return (
                  <div key={key} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    background: '#1e293b', borderRadius: '8px', padding: '8px 12px', fontSize: '12px',
                  }}>
                    <span style={{ color: isOn ? '#e2e8f0' : '#64748b', fontWeight: 500 }}>{label}</span>
                    <span style={{
                      fontSize: '10px', fontWeight: 700, padding: '2px 8px', borderRadius: '6px', fontFamily: 'monospace',
                      background: isOn ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
                      color: isOn ? '#22c55e' : '#ef4444',
                    }}>
                      {isOn ? 'ACTIVE' : 'DISABLED'}
                    </span>
                  </div>
                );
              })}
              <div style={{ fontSize: '10px', color: '#64748b', marginTop: '4px', fontStyle: 'italic' }}>
                Toggle detectors from the Filters sidebar on the left. Disabled categories are completely skipped during AI inference.
              </div>
            </div>
          </div>

          {/* Progress & Status */}
          <div style={{
            background: '#020617cc', borderRadius: '12px', padding: '16px',
            border: '1px solid #1e293b', display: 'flex', flexDirection: 'column', gap: '10px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '12px' }}>
              <span style={{ color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '6px' }}>
                {isProcessing
                  ? <RefreshCw style={{ width: 14, height: 14, color: '#818cf8', animation: 'spin 1s linear infinite' }} />
                  : <CheckCircle2 style={{ width: 14, height: 14, color: '#34d399' }} />
                }
                {statusMessage}
              </span>
              <span style={{ fontFamily: 'monospace', fontWeight: 700, color: '#818cf8' }}>{progress.toFixed(0)}%</span>
            </div>
            <div style={{ width: '100%', background: '#1e293b', borderRadius: '999px', height: '8px', overflow: 'hidden' }}>
              <div style={{
                width: `${progress}%`, height: '100%', borderRadius: '999px',
                background: 'linear-gradient(90deg, #6366f1, #818cf8)',
                transition: 'width 0.3s ease',
              }} />
            </div>
          </div>

          {/* Model Accuracy Panel */}
          {modelAccuracy.total > 0 && (
            <div style={{
              background: '#020617cc', borderRadius: '12px', padding: '16px',
              border: '1px solid #1e293b',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px' }}>
                <Target style={{ width: 14, height: 14, color: '#22d3ee' }} />
                <span style={{ fontSize: '11px', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Model Accuracy & Confidence Report
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '12px' }}>
                <div style={{ background: '#1e293b', borderRadius: '8px', padding: '10px', textAlign: 'center' }}>
                  <div style={{ fontSize: '20px', fontWeight: 800, color: '#22d3ee', fontFamily: 'monospace' }}>
                    {(modelAccuracy.avgConf * 100).toFixed(1)}%
                  </div>
                  <div style={{ fontSize: '10px', color: '#94a3b8', fontWeight: 600, marginTop: '2px' }}>
                    AVG CONFIDENCE
                  </div>
                </div>
                <div style={{ background: '#1e293b', borderRadius: '8px', padding: '10px', textAlign: 'center' }}>
                  <div style={{ fontSize: '20px', fontWeight: 800, color: '#a78bfa', fontFamily: 'monospace' }}>
                    {modelAccuracy.total}
                  </div>
                  <div style={{ fontSize: '10px', color: '#94a3b8', fontWeight: 600, marginTop: '2px' }}>
                    TOTAL DETECTIONS
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {Object.entries(modelAccuracy.byClass).map(([cls, stats]) => (
                  <div key={cls} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    background: '#1e293b', borderRadius: '8px', padding: '8px 12px', fontSize: '11px',
                  }}>
                    <span style={{ color: '#e2e8f0', fontWeight: 600, textTransform: 'uppercase' }}>{cls.replace(/_/g, ' ')}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span style={{ color: '#94a3b8', fontFamily: 'monospace' }}>x{stats.count}</span>
                      <span style={{
                        fontFamily: 'monospace', fontWeight: 700, padding: '2px 8px', borderRadius: '6px',
                        background: stats.avgConf >= 0.85 ? 'rgba(34,211,238,0.15)' : 'rgba(251,191,36,0.15)',
                        color: stats.avgConf >= 0.85 ? '#22d3ee' : '#fbbf24',
                      }}>
                        {(stats.avgConf * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Live Detections Stream */}
          {detectedLog.length > 0 && (
            <div style={{
              background: '#020617cc', borderRadius: '12px', padding: '16px',
              border: '1px solid #1e293b',
            }}>
              <div style={{ fontSize: '11px', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>
                Live Detections Broadcasted to GIS Map ({detectedLog.length})
              </div>
              <div style={{ maxHeight: '160px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '6px', paddingRight: '4px' }}>
                {detectedLog.map((log) => (
                  <div key={log.id} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    background: '#0f172a', padding: '8px 10px', borderRadius: '8px',
                    border: '1px solid #1e293b', fontSize: '11px',
                  }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#fbbf24' }}>
                      <AlertTriangle style={{ width: 14, height: 14 }} />
                      {log.class_name.replace(/_/g, ' ').toUpperCase()}
                    </span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {log.risk_score !== undefined && (
                        <span style={{
                          fontSize: '10px', fontWeight: 700, fontFamily: 'monospace', padding: '2px 6px', borderRadius: '4px',
                          background: log.risk_score >= 85 ? 'rgba(239,68,68,0.2)' : (log.risk_score >= 65 ? 'rgba(249,115,22,0.2)' : 'rgba(245,158,11,0.2)'),
                          color: log.risk_score >= 85 ? '#ef4444' : (log.risk_score >= 65 ? '#f97316' : '#f59e0b'),
                        }}>
                          RISK {Math.round(log.risk_score)}
                        </span>
                      )}
                      <span style={{
                        fontFamily: 'monospace', fontWeight: 700, padding: '2px 6px', borderRadius: '4px',
                        background: log.conf >= 0.85 ? 'rgba(34,211,238,0.15)' : 'rgba(251,191,36,0.15)',
                        color: log.conf >= 0.85 ? '#22d3ee' : '#fbbf24', fontSize: '10px',
                      }}>
                        {(log.conf * 100).toFixed(0)}%
                      </span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${sevColor(log.severity)}`}
                        style={{ fontSize: '10px', fontWeight: 600, fontFamily: 'monospace' }}>
                        SEV {log.severity}
                      </span>
                      <span style={{ fontSize: '10px', color: '#64748b', fontFamily: 'monospace' }}>{log.time}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── Footer ── */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '12px',
          padding: '14px 24px', borderTop: '1px solid #1e293b',
        }}>
          <button type="button" onClick={onClose}
            style={{
              padding: '8px 16px', borderRadius: '8px', fontSize: '12px', fontWeight: 600,
              color: '#cbd5e1', background: 'transparent', border: 'none', cursor: 'pointer',
            }}>
            Close
          </button>
          <button type="button" disabled={isProcessing} onClick={handleStartProcessing}
            style={{
              display: 'flex', alignItems: 'center', gap: '8px',
              background: isProcessing ? '#4338ca' : '#4f46e5',
              color: '#fff', fontWeight: 700, fontSize: '12px',
              padding: '10px 20px', borderRadius: '8px', border: 'none',
              cursor: isProcessing ? 'not-allowed' : 'pointer',
              opacity: isProcessing ? 0.7 : 1,
              boxShadow: '0 4px 14px rgba(99,102,241,0.35)',
            }}>
            {isProcessing
              ? <RefreshCw style={{ width: 16, height: 16, animation: 'spin 1s linear infinite' }} />
              : <Play style={{ width: 16, height: 16 }} />
            }
            {isProcessing ? 'Processing Edge Video...' : 'Run Edge AI Perception'}
          </button>
        </div>
      </div>

      {/* Keyframe animation for spinner */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>,
    document.body
  );
}
