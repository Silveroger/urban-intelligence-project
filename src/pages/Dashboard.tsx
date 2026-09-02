import { useState, useMemo, useEffect, useCallback } from 'react';
import { GpsConsole } from '../components/GpsPipeline/GpsConsole';
import { Inspector } from '../components/Details/Inspector';
import { FilterPanel } from '../components/Sidebar/FilterPanel';
import { KpiCards } from '../components/Cards/KpiCards';
import { VideoProcessingHub } from '../components/VideoHub/VideoProcessingHub';
import { fetchSegments, fetchEvents, fetchIncidents, fetchBuses, fetchSegmentHistory } from '../services/api';
import { connectWebSocket, disconnectWebSocket } from '../services/websocket';
import type { WSMessage } from '../services/websocket';
import type { SegmentHistory } from '../services/api';
import type { FilterState } from '../types/filters';
import { DEFAULT_FILTERS } from '../types/filters';
import type { RoadSegment } from '../types/roadSegments';
import type { Event } from '../types/events';
import type { Incident } from '../types/incidents';
import type { Bus } from '../types/buses';
import type { GpsRecord } from '../types/gps';
import { Video, Radio } from 'lucide-react';
import { isSupabaseConfigured } from '../services/supabase';

export function Dashboard() {
  // ─── Backend data state ───
  const [segments, setSegments] = useState<RoadSegment[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [buses, setBuses] = useState<Bus[]>([]);
  const [loading, setLoading] = useState(true);

  // ─── Selection state ───
  const [selectedRoad, setSelectedRoad] = useState<RoadSegment | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [selectedGpsRecord, setSelectedGpsRecord] = useState<GpsRecord | null>(null);
  const [segmentHistory, setSegmentHistory] = useState<SegmentHistory>([]);

  // ─── Filter & Modal state ───
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [videoHubOpen, setVideoHubOpen] = useState(false);

  // Load initial data via API provider
  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      const [seg, evt, inc, bus] = await Promise.all([
        fetchSegments(),
        fetchEvents(),
        fetchIncidents(),
        fetchBuses(),
      ]);
      if (cancelled) return;
      setSegments(seg);
      setEvents(evt);
      setIncidents(inc);
      setBuses(bus);
      setLoading(false);
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  // Connect WebSocket for live telemetry stream
  useEffect(() => {
    const handleWsMessage = (msg: WSMessage) => {
      if (msg.type === 'NEW_EVENT') {
        const newEvt = msg.payload as Event;
        setEvents((prev) => [newEvt, ...prev.filter((e) => e.event_id !== newEvt.event_id)]);
      } else if (msg.type === 'NEW_INCIDENT') {
        const newInc = msg.payload as Incident;
        setIncidents((prev) => [newInc, ...prev.filter((i) => i.incident_id !== newInc.incident_id)]);
      } else if (msg.type === 'BUS_TELEMETRY') {
        const newBus = msg.payload as Bus;
        setBuses((prev) => {
          const idx = prev.findIndex((b) => b.bus_id === newBus.bus_id);
          if (idx >= 0) {
            const copy = [...prev];
            copy[idx] = newBus;
            return copy;
          }
          return [...prev, newBus];
        });
      } else if (msg.type === 'SEGMENT_UPDATE') {
        const updated = msg.payload;
        setSegments((prev) => {
          if (!Array.isArray(prev)) return [];
          const sid = updated.properties?.segment_id || updated.id || updated.segment_id;
          const newProps = updated.properties || updated;
          return prev.map((s) => (s.segment_id === sid ? { ...s, ...newProps } : s));
        });
      }
    };

    connectWebSocket(handleWsMessage);
    return () => {
      disconnectWebSocket();
    };
  }, []);

  // Load segment history when a road is selected
  useEffect(() => {
    if (!selectedRoad) return;
    let cancelled = false;
    fetchSegmentHistory(selectedRoad.segment_id).then((h) => {
      if (!cancelled) setSegmentHistory(h);
    });
    return () => {
      cancelled = true;
    };
  }, [selectedRoad]);

  // Derived: filtered events
  const filteredEvents = useMemo(() => {
    return events.filter((e) => {
      if (!filters.eventTypes[e.event_type]) return false;
      if (e.severity !== undefined && e.severity < filters.minSeverity) return false;
      if (e.confidence < filters.minConfidence) return false;
      return true;
    });
  }, [events, filters]);

  // Selection handlers
  const handleSelectGpsRecord = useCallback((record: GpsRecord | null) => {
    setSelectedGpsRecord(record);
    setSelectedRoad(null);
    setSelectedEvent(null);
    setSelectedIncident(null);
  }, []);

  const handleCloseInspector = useCallback(() => {
    setSelectedRoad(null);
    setSelectedEvent(null);
    setSelectedIncident(null);
    setSelectedGpsRecord(null);
    setSegmentHistory([]);
  }, []);

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-brand">
          <span className="brand-dot"></span>
          <h1 className="brand-title">SIH 26124 — GPS Collection & Supabase Telemetry Pipeline</h1>
          <span className="brand-badge">
            <Radio className="w-3 h-3 inline mr-1" />
            Ingestion Node
          </span>
        </div>
        <div className="header-meta">
          <button
            type="button"
            onClick={() => setVideoHubOpen(true)}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-lg text-xs font-semibold shadow-md transition"
          >
            <Video className="w-3.5 h-3.5" />
            <span>Edge Video & GPS Hub</span>
          </button>
          <span className="meta-item">
            Region: <strong>Chandigarh</strong>
          </span>
          <span className="meta-item">
            Supabase: <strong>{isSupabaseConfigured ? 'Connected' : 'Simulated'}</strong>
          </span>
          <button
            type="button"
            className="sidebar-toggle-btn"
            onClick={() => setSidebarOpen((v) => !v)}
            aria-label="Toggle filters"
            title="Toggle Filters Sidebar"
          >
            ☰
          </button>
        </div>
      </header>

      <div className="kpi-row">
        <KpiCards segments={segments} events={filteredEvents} incidents={incidents} buses={buses} />
      </div>

      <main className="app-main">
        {sidebarOpen && (
          <aside className="filter-sidebar">
            <FilterPanel filters={filters} onChange={setFilters} />
          </aside>
        )}

        {/* ── Main GPS Telemetry & Ingestion Console (Zero Map Rendering) ── */}
        <div className="gps-main-workspace">
          {loading ? (
            <div className="loading-overlay">Initializing GPS Telemetry Engine…</div>
          ) : (
            <GpsConsole
              onSelectRecord={handleSelectGpsRecord}
              selectedRecord={selectedGpsRecord}
            />
          )}
        </div>

        <aside className="inspector-sidebar">
          <Inspector
            selectedRoad={selectedRoad}
            selectedEvent={selectedEvent}
            selectedIncident={selectedIncident}
            selectedGpsRecord={selectedGpsRecord}
            segmentHistory={segmentHistory}
            onClose={handleCloseInspector}
          />
        </aside>
      </main>

      {/* Edge Video & GPS Ingestion Modal */}
      <VideoProcessingHub
        isOpen={videoHubOpen}
        onClose={() => setVideoHubOpen(false)}
        filters={filters}
        onNewEvent={(evt) => setEvents((prev) => [evt, ...prev])}
        onNewIncident={(inc) => setIncidents((prev) => [inc, ...prev])}
      />
    </div>
  );
}
