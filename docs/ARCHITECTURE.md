# System Architecture

## 1. Architectural Overview
The SIH 26124 platform is a distributed geospatial intelligence system that converts continuous edge telemetry and computer vision detections into persistent, aggregate road health and traffic intelligence visualized on a decision-support dashboard.

```text
┌────────────────────────────────────────────────────────┐
│             Mobile Sensing Fleet (Buses)               │
│  [Camera Sensors] + [GPS Receiver] + [Edge Hardware]   │
└───────────────────────────┬────────────────────────────┘
                            │ Telemetry (GPS) & Perception Metadata
                            ▼
┌────────────────────────────────────────────────────────┐
│             FastAPI Backend Services                   │
│  - POST /api/v1/telemetry    (GPS Trace Ingestion)     │
│  - POST /api/v1/observations (AI Perception Ingest)    │
│  - GET /api/v1/segments/geojson (Canonical Network)    │
│  - GET /api/v1/analytics/summary (Citywide KPIs)       │
│  - Services: Ingestion, Map Matching, Scoring Engine   │
│  - Evidence Service (Supabase Storage 'road-evidence') │
│  - WebSocket Broadcaster (/ws/live)                    │
│    (BUS_TELEMETRY, NEW_EVENT, NEW_INCIDENT,            │
│     SEGMENT_UPDATE, Heartbeat PING/PONG)               │
│  - HTTP 503 Database Error Gateway (No SQLite fallback)│
└───────────────────────────┬────────────────────────────┘
                            │ Validated State & Spatial Queries
                            ▼
┌────────────────────────────────────────────────────────┐
│          Geospatial Processing & Persistence           │
│  - PostgreSQL 17.6 + PostGIS 3.3.7 ('gis' Schema)      │
│  - Regional IPv4 Session Pooler (search_path: public,gis)
│  - OSM-Derived Canonical Road Geometries (EPSG:4326)   │
│  - Tables: buses, routes, trips, road_segments,        │
│            gps_points, observations, incidents,        │
│            segment_history                             │
│  - Compatibility View: gps_records (maps over gps_points)
│  - GiST Spatial Indexing (geometry columns)            │
└───────────────────────────┬────────────────────────────┘
                            │ REST API (Hydration) + WebSocket (Live Deltas)
                            ▼
┌────────────────────────────────────────────────────────┐
│             GIS Frontend / Urban Dashboard             │
│  - React 19 + TypeScript + Vite + Tailwind CSS         │
│  - Google Maps Vector API (Map ID) + deck.gl Overlay   │
│  - Single Coordinate Boundary (geoJsonToGooglePath)    │
│  - Live State: VITE_USE_MOCK=false                     │
│  - WebSocket Client with Exponential Backoff & Heartbeat
│  - Segment, Event & Incident Inspector Drawers         │
│  - Historical Degradation Trends & KPI Analytics       │
└────────────────────────────────────────────────────────┘
```

---

## 2. Subsystem Boundaries & Responsibilities

### 2.1 Edge & Telemetry Subsystem
- **Responsibilities:** Continuous video sampling, GPS coordinate capture, local frame filtering, metadata packaging, and edge event triggering.
- **Outputs:** Event observation payloads with synchronized timestamps and spatial coordinates.

### 2.2 AI / Perception Subsystem
- **Responsibilities:** Object detection and segmentation for potholes, surface cracks, waterlogging; vehicle detection and tracking; OCR on license plates.
- **Constraints:** Outputs structured JSON payloads conforming to [`docs/AI_CONTRACT.md`](AI_CONTRACT.md). Does not execute directly within the frontend.

### 2.3 Backend & Geospatial Subsystem (`backend/`)
- **Responsibilities:** Ingestion validation, spatial road-network map matching, multi-pass observation aggregation, dynamic condition scoring ($0-100$), confidence estimation, clean-pass recovery, historical state maintenance, and API delivery.
- **Connectivity:** Uses Supabase Regional IPv4 Session Pooler on port 5432 with `connect_args={"server_settings": {"search_path": "public, gis"}}`. Eliminates silent SQLite fallback, routing database connection errors to HTTP 503 `DATABASE_CONNECTION_ERROR`.
- **Core Implemented Modules:**
  - `app/services/ingestion.py`: Validates perception payloads, enforces OCR plate confidence rules, quarantines low-confidence observations ($< 0.50$, stored with `status = 'quarantined'`, HTTP 201), map-matches confirmed detections, updates road score, and broadcasts `NEW_EVENT`.
  - `app/services/map_matching.py`: Executes spatial snapping to nearest road segment using PostGIS `gis.ST_DWithin` and `gis.ST_Distance`.
  - `app/services/scoring.py`: Computes deterministic road condition scores ($0-100$) with repeat-defect multipliers, confidence penalty scaling (`weight_by_confidence=True`), and clean-pass recovery credits (+5.0 condition points per clean pass).
  - `app/services/aggregation.py`: Recalculates segment metrics (`pothole_count`, `waterlogging_count`, `observation_count`), debounces history snapshot insertion to 10-second intervals (BUG-006 resolution), and broadcasts `SEGMENT_UPDATE` frames (BUG-017 resolution).
  - `app/services/telemetry.py`: Ingests vehicle GPS points into authoritative `gps_points` table, updates latest bus position, and broadcasts `BUS_TELEMETRY` frames.
  - `app/services/incidents.py`: Manages traffic violations and obstructions, generates signed evidence URLs, and broadcasts `NEW_INCIDENT` frames (BUG-016 resolution).
  - `app/services/evidence.py`: Integrates with Supabase Storage (`road-evidence` bucket) to store defect crops and dynamically generates 1-hour signed URLs.
  - `app/api/v1/analytics.py`: Computes aggregate citywide infrastructure KPIs (average score, condition distribution tiers, active fleet, defect and incident counts).
  - `app/websocket/manager.py`: Thread-safe broadcast connection manager distributing live frames (`BUS_TELEMETRY`, `NEW_EVENT`, `NEW_INCIDENT`, `SEGMENT_UPDATE`) to connected clients with dead connection pruning and heartbeat ping/pong handling.
- **Persistence & GPS Architecture:**
  - `gps_points` is the authoritative physical table for raw telemetry.
  - `gps_records` is a permanent compatibility VIEW over `gps_points`. Do NOT create competing GPS pipelines.
  - 9 reconciled canonical entities: `buses`, `routes`, `trips`, `road_segments`, `gps_points`, `gps_records` (view), `observations`, `incidents`, `segment_history`. See [`docs/DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md).

### 2.4 Canonical Road Geometry Pipeline (OSM-Derived)
- **Problem Solved:** Previously, the database and mock datasets contained coarse synthetic road lines with only 2 to 4 vertices per road. These straight lines cut across city sectors and did not follow the physical street corridors on the Google Maps vector basemap.
- **Canonical Source of Truth:** Authentic road centerlines were extracted from OpenStreetMap (OSM) for Chandigarh's primary arterial corridors (Jan Marg, Madhya Marg, Dakshin Marg, Purv Marg, Vigyan Marg, Sarovar Path, Himalaya Marg, Sukhna Path, Udyog Path, and Vidya Path).
- **Persistent Asset:** The canonical dataset is permanently versioned in [`backend/data/chandigarh_roads_canonical.geojson`](../backend/data/chandigarh_roads_canonical.geojson) and loaded into `public.road_segments.geom` in PostGIS.
- **Coordinate Standard:** All geometries strictly use WGS84 (EPSG:4326) with 13 to 38 vertices per segment, capturing genuine road curvatures and intersections.
- **Spatial Alignment:** Fleet bus simulation paths (`simulate_chandigarh_buses.py`), AI defect observations, and traffic incidents are snapped to and traverse along these canonical coordinates with verified $0.00\,\text{m}$ spatial offset.
- **Rendering Isolation:** GeoJSON `[longitude, latitude]` arrays are converted once to Google Maps `{lat, lng}` coordinates via `geoJsonToGooglePath` inside `src/utils/coordinates.ts`.

### 2.5 GIS Frontend Dashboard (`src/`)
- **Responsibilities:** Hardware-accelerated map visualization, colored road segment polylines, Advanced Markers, deck.gl density heatmaps, filter state management, analytics charts, and drill-down inspection drawers.
- **Live Configuration:** Operates with `VITE_USE_MOCK=false` against the FastAPI backend, with real-time WebSocket deltas updating moving buses and segment degradation colors without full-page reloads.
- **Constraints:** Consumes backend data via [`docs/API_CONTRACT.md`](API_CONTRACT.md) and renders truth; does not calculate spatial matching or condition scoring algorithms client-side. See [`docs/FRONTEND_ARCHITECTURE.md`](FRONTEND_ARCHITECTURE.md).

---

## 3. Integration Architecture & Data Flow

### 3.1 Data Flow Patterns
1. **Initial State Hydration (REST):** Upon page load, the frontend issues asynchronous REST requests (`/api/v1/segments/geojson`, `/api/v1/events`, `/api/v1/incidents`, `/api/v1/buses`, `/api/v1/analytics/summary`) to populate the complete map viewport, summary cards, and inspector drawers.
2. **Real-Time Streaming (WebSocket):** The frontend opens a persistent connection to `/ws/live`. The backend emits delta payloads for live bus coordinates (`BUS_TELEMETRY`), newly confirmed defects (`NEW_EVENT`), traffic incident alerts (`NEW_INCIDENT`), and segment metric updates (`SEGMENT_UPDATE`). The frontend client implements auto-reconnect with exponential backoff (1s to 30s) and 30-second ping heartbeats.
3. **Graceful Degradation:** If the WebSocket connection drops, the frontend automatically attempts reconnection while maintaining full operational capability using hydrated REST state without crashing the UI.

### 3.2 Integration Checklist & Pre-Flight Verification
Before connecting a new service, edge node, or API endpoint, verify:
- **Contract Adherence:** Ensure payload strictly adheres to [`docs/API_CONTRACT.md`](API_CONTRACT.md) and [`docs/AI_CONTRACT.md`](AI_CONTRACT.md).
- **Coordinate Standard:** Interchanged coordinates must use GeoJSON `[longitude, latitude]` format (EPSG:4326).
- **Canonical Road Alignment:** Ensure all simulated or real vehicle routes and detection coordinates match the OSM-derived canonical corridors in `backend/data/chandigarh_roads_canonical.geojson`.
- **Timestamp Standard:** All timestamps must use ISO-8601 with explicit timezone offsets (e.g., `2026-08-29T18:42:11+05:30`).
- **Identifier Stability:** All entities (`segment_id`, `event_id`, `bus_id`, `incident_id`) must use deterministic, unique string IDs.
- **Nullability & Defaults:** Optional fields (`heading_deg`, `evidence_uri`, `plate_text`) must be nullable without breaking schema deserialization.
- **Evidence Formatting:** Media references must be fully qualified HTTPS URLs or valid storage paths, not unbounded Base64 strings.
- **Known Discrepancies:** Consult [`docs/BUGS_AND_DISCREPANCIES.md`](BUGS_AND_DISCREPANCIES.md) for resolved and active interface alignments.
