import { useState, useMemo, useEffect, useCallback } from 'react';
import { GoogleMapView } from '../components/Map/GoogleMapView';
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
import { Video } from 'lucide-react';

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
  const [segmentHistory, setSegmentHistory] = useState<SegmentHistory>([]);

  // ─── Filter & UI state ───
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [sidebarOpen, setSidebarOpen] = useState(true);
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

  // Selection handlers — clear other selections
  const handleSelectRoad = useCallback((road: RoadSegment) => {
    setSelectedRoad(road);
    setSelectedEvent(null);
    setSelectedIncident(null);
  }, []);

  const handleSelectEvent = useCallback((event: Event) => {
    setSelectedEvent(event);
    setSelectedRoad(null);
    setSelectedIncident(null);
    setSegmentHistory([]);
  }, []);

  const handleSelectIncident = useCallback((incident: Incident) => {
    setSelectedIncident(incident);
    setSelectedRoad(null);
    setSelectedEvent(null);
    setSegmentHistory([]);
  }, []);

  const handleCloseInspector = useCallback(() => {
    setSelectedRoad(null);
    setSelectedEvent(null);
    setSelectedIncident(null);
    setSegmentHistory([]);
  }, []);

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-brand">
          <span className="brand-dot"></span>
          <h1 className="brand-title">SIH 26124 — Urban Intelligence GIS</h1>
          <span className="brand-badge">P0 Dashboard</span>
        </div>
        <div className="header-meta">
          <button
            type="button"
            onClick={() => setVideoHubOpen(true)}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-lg text-xs font-semibold shadow-md transition"
          >
            <Video className="w-3.5 h-3.5" />
            <span>Edge AI Video Hub</span>
          </button>
          <span className="meta-item">
            Region: <strong>Chandigarh</strong>
          </span>
          <span className="meta-item">
            Data: <strong>{import.meta.env.VITE_USE_MOCK === 'true' ? 'Mock' : 'Live'}</strong>
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

        <div className="map-wrapper">
          {loading ? (
            <div className="loading-overlay">Loading map & GIS layers…</div>
          ) : (
            <GoogleMapView
              roadSegments={segments}
              events={filteredEvents}
              incidents={incidents}
              buses={buses}
              filters={filters}
              selectedRoad={selectedRoad}
              selectedEvent={selectedEvent}
              selectedIncident={selectedIncident}
              onSelectRoad={handleSelectRoad}
              onSelectEvent={handleSelectEvent}
              onSelectIncident={handleSelectIncident}
            />
          )}
        </div>

        <aside className="inspector-sidebar">
          <Inspector
            selectedRoad={selectedRoad}
            selectedEvent={selectedEvent}
            selectedIncident={selectedIncident}
            segmentHistory={segmentHistory}
            onClose={handleCloseInspector}
          />
        </aside>
      </main>

      {/* Edge Video Ingestion Modal */}
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
