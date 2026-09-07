import { useState, useMemo, useEffect, useCallback } from 'react';
import { GoogleMapView } from '../components/Map/GoogleMapView';
import { Inspector } from '../components/Details/Inspector';
import { FilterPanel } from '../components/Sidebar/FilterPanel';
import { KpiCards } from '../components/Cards/KpiCards';
import { fetchSegments, fetchEvents, fetchIncidents, fetchBuses, fetchSegmentHistory } from '../services/api';
import { connectLiveStream, disconnectLiveStream } from '../services/websocket';
import type { WebSocketStatus } from '../services/websocket';
import type { SegmentHistory } from '../services/api';
import type { FilterState } from '../types/filters';
import { DEFAULT_FILTERS } from '../types/filters';
import type { RoadSegment } from '../types/roadSegments';
import type { Event } from '../types/events';
import type { Incident } from '../types/incidents';
import type { Bus } from '../types/buses';
import { Video } from 'lucide-react';
import { VideoProcessingHub } from '../components/VideoHub/VideoProcessingHub';

export function Dashboard() {
  // ─── Backend data state ───
  const [segments, setSegments] = useState<RoadSegment[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [buses, setBuses] = useState<Bus[]>([]);
  const [loading, setLoading] = useState(true);
  const [wsStatus, setWsStatus] = useState<WebSocketStatus>('disconnected');

  // ─── Selection state ───
  const [selectedRoad, setSelectedRoad] = useState<RoadSegment | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [selectedBus, setSelectedBus] = useState<Bus | null>(null);
  const [segmentHistory, setSegmentHistory] = useState<SegmentHistory>([]);

  // ─── Filter state ───
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);

  // ─── UI state ───
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
    return () => { cancelled = true; };
  }, []);

  // Connect to live WebSocket stream for real-time telemetry and defect events
  useEffect(() => {
    if (import.meta.env.VITE_USE_MOCK === 'true') {
      return;
    }

    connectLiveStream({
      onStatusChange: (status) => {
        setWsStatus(status);
      },
      onBusTelemetry: (telemetry) => {
        setBuses((prev) => {
          const idx = prev.findIndex(
            (b) => b.bus_id === telemetry.bus_id || (b.vehicle_number && b.vehicle_number === telemetry.bus_id)
          );
          if (idx >= 0) {
            const next = [...prev];
            next[idx] = { ...next[idx], ...telemetry };
            return next;
          }
          return [...prev, telemetry];
        });

        setSelectedBus((curr) => {
          if (curr && (curr.bus_id === telemetry.bus_id || curr.vehicle_number === telemetry.bus_id)) {
            return { ...curr, ...telemetry };
          }
          return curr;
        });
      },
      onNewEvent: (newEvent) => {
        setEvents((prev) => {
          if (prev.some((e) => e.event_id === newEvent.event_id)) return prev;
          return [newEvent, ...prev];
        });
      },
      onNewIncident: (newIncident) => {
        setIncidents((prev) => {
          if (prev.some((i) => i.incident_id === newIncident.incident_id)) return prev;
          return [newIncident, ...prev];
        });
      },
      onSegmentUpdate: (update) => {
        setSegments((prev) =>
          prev.map((s) => {
            if (s.segment_id === update.segment_id) {
              return {
                ...s,
                condition_score: update.condition_score ?? s.condition_score,
                pothole_count: update.pothole_count,
                waterlogging_count: update.waterlogging_count,
                observation_count: update.observation_count,
                last_updated: update.last_updated || s.last_updated,
              };
            }
            return s;
          })
        );
      },
    });

    return () => {
      disconnectLiveStream();
    };
  }, []);

  // Load segment history when a road is selected
  useEffect(() => {
    if (!selectedRoad) return;
    let cancelled = false;
    fetchSegmentHistory(selectedRoad.segment_id).then((h) => {
      if (!cancelled) setSegmentHistory(h);
    });
    return () => { cancelled = true; };
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
    setSelectedBus(null);
  }, []);

  const handleSelectEvent = useCallback((event: Event) => {
    setSelectedEvent(event);
    setSelectedRoad(null);
    setSelectedIncident(null);
    setSelectedBus(null);
    setSegmentHistory([]);
  }, []);

  const handleSelectIncident = useCallback((incident: Incident) => {
    setSelectedIncident(incident);
    setSelectedRoad(null);
    setSelectedEvent(null);
    setSelectedBus(null);
    setSegmentHistory([]);
  }, []);

  const handleSelectBus = useCallback((bus: Bus) => {
    setSelectedBus(bus);
    setSelectedRoad(null);
    setSelectedEvent(null);
    setSelectedIncident(null);
    setSegmentHistory([]);
  }, []);

  const handleCloseInspector = useCallback(() => {
    setSelectedRoad(null);
    setSelectedEvent(null);
    setSelectedIncident(null);
    setSelectedBus(null);
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
          <span className="meta-item">Region: <strong>Chandigarh</strong></span>
          <span className="meta-item">
            Source: <strong>{import.meta.env.VITE_USE_MOCK === 'true' ? 'Mock Data' : 'Live Supabase/FastAPI'}</strong>
          </span>
          {import.meta.env.VITE_USE_MOCK !== 'true' && (
            <span
              className="meta-item"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontWeight: 500,
                color:
                  wsStatus === 'connected'
                    ? '#22c55e'
                    : wsStatus === 'connecting'
                      ? '#f59e0b'
                      : '#94a3b8',
              }}
            >
              <span
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor:
                    wsStatus === 'connected'
                      ? '#22c55e'
                      : wsStatus === 'connecting'
                        ? '#f59e0b'
                        : '#94a3b8',
                  boxShadow: wsStatus === 'connected' ? '0 0 8px #22c55e' : undefined,
                }}
              />
              {wsStatus === 'connected' ? 'WebSocket Live' : wsStatus === 'connecting' ? 'Connecting Live...' : 'Offline'}
            </span>
          )}
          <button
            type="button"
            onClick={() => setVideoHubOpen(true)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#4f46e5',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              marginRight: '8px',
              boxShadow: '0 2px 8px rgba(79, 70, 229, 0.35)',
            }}
          >
            <Video style={{ width: 14, height: 14 }} />
            <span>Edge AI Video Hub</span>
          </button>
          <button
            type="button"
            className="sidebar-toggle-btn"
            onClick={() => setSidebarOpen((v) => !v)}
            aria-label="Toggle filters"
          >
            ☰
          </button>
        </div>
      </header>

      <div className="kpi-row">
        <KpiCards
          segments={segments}
          events={filteredEvents}
          incidents={incidents}
          buses={buses}
        />
      </div>

      <main className="app-main">
        {sidebarOpen && (
          <aside className="filter-sidebar">
            <FilterPanel filters={filters} onChange={setFilters} />
          </aside>
        )}

        <div className="map-wrapper">
          {loading ? (
            <div className="loading-overlay">Loading data…</div>
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
              selectedBus={selectedBus}
              onSelectRoad={handleSelectRoad}
              onSelectEvent={handleSelectEvent}
              onSelectIncident={handleSelectIncident}
              onSelectBus={handleSelectBus}
            />
          )}
        </div>

        <aside className="inspector-sidebar">
          <Inspector
            selectedRoad={selectedRoad}
            selectedEvent={selectedEvent}
            selectedIncident={selectedIncident}
            selectedBus={selectedBus}
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
        onNewEvent={(newEvent) => {
          setEvents((prev) => {
            if (prev.some((e) => e.event_id === newEvent.event_id)) return prev;
            return [newEvent, ...prev];
          });
        }}
        onNewIncident={(newIncident) => {
          setIncidents((prev) => {
            if (prev.some((i) => i.incident_id === newIncident.incident_id)) return prev;
            return [newIncident, ...prev];
          });
        }}
      />
    </div>
  );
}

