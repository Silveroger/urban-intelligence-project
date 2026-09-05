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
│  - Services: Ingestion, Map Matching, Scoring Engine   │
│  - Evidence Service (Supabase Storage 'road-evidence') │
│  - WebSocket Broadcaster (/ws/live)                    │
└───────────────────────────┬────────────────────────────┘
                            │ Validated State & Spatial Queries
                            ▼
┌────────────────────────────────────────────────────────┐
│          Geospatial Processing & Persistence           │
│  - PostgreSQL + PostGIS (Functions in 'gis' Schema)    │
│  - Tables: road_segments, observations, incidents,     │
│            segment_history, buses, gps_points          │
│  - GiST Spatial Indexing (geometry columns)            │
└───────────────────────────┬────────────────────────────┘
                            │ REST API (Hydration) + WebSocket (Live Deltas)
                            ▼
┌────────────────────────────────────────────────────────┐
│             GIS Frontend / Urban Dashboard             │
│  - React 19 + TypeScript + Vite + Tailwind CSS         │
│  - Google Maps Vector API (Map ID) + deck.gl Overlay   │
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
- **Responsibilities:** Ingestion validation, spatial road-network map matching, multi-pass observation aggregation, dynamic condition scoring ($0-100$), confidence estimation, historical state maintenance, and API delivery.
- **Core Implemented Modules:**
  - `app/services/ingestion.py`: Validates perception payloads, enforces confidence threshold (quarantined if $< 0.50$), triggers map matching, updates road score, and broadcasts `NEW_EVENT`.
  - `app/services/map_matching.py`: Executes spatial snapping to nearest road segment using PostGIS `gis.ST_DWithin` and `gis.ST_Distance`.
  - `app/services/scoring.py`: Computes deterministic road condition scores ($0-100$) and condition tiers (`good`, `fair`, `poor`, `critical`) with repeat-defect escalation multipliers.
  - `app/services/aggregation.py`: Recalculates segment aggregates (`pothole_count`, `waterlogging_count`) and inserts historical snapshots into `segment_history`.
  - `app/services/telemetry.py`: Ingests vehicle GPS points into `gps_points`, updates latest bus position, and broadcasts `BUS_TELEMETRY` frames.
  - `app/services/evidence.py`: Integrates with Supabase Storage (`road-evidence` bucket) to store defect image crops and generate signed URLs.
  - `app/websocket/manager.py`: Thread-safe broadcast connection manager distributing live frames to all connected web clients.
- **Persistence:** Relational schema and spatial layers in PostgreSQL/PostGIS (see [`docs/DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md)).

### 2.4 GIS Frontend Dashboard (`src/`)
- **Responsibilities:** Hardware-accelerated map visualization, colored road segment polylines, Advanced Markers, deck.gl density heatmaps, filter state management, analytics charts, and drill-down inspection drawers.
- **Constraints:** Consumes backend data via [`docs/API_CONTRACT.md`](API_CONTRACT.md) and renders truth; does not calculate spatial matching or condition scoring algorithms client-side. See [`docs/FRONTEND_ARCHITECTURE.md`](FRONTEND_ARCHITECTURE.md).

---

## 3. Integration Architecture & Data Flow

### 3.1 Data Flow Patterns
1. **Initial State Hydration (REST):** Upon page load, the frontend issues asynchronous REST requests (`/api/v1/segments/geojson`, `/api/v1/events`, `/api/v1/incidents`, `/api/v1/buses`) to populate the complete map viewport and initial statistics.
2. **Real-Time Streaming (WebSocket):** The frontend opens a persistent connection to `/ws/live`. The backend emits delta payloads for live bus coordinates (`BUS_TELEMETRY`), newly confirmed defects (`NEW_EVENT`), and incident alerts.
3. **Graceful Degradation:** If the WebSocket connection drops, the frontend maintains full operational capability using REST polling or cached state without crashing the UI.

### 3.2 Integration Checklist & Pre-Flight Verification
Before connecting a new service, edge node, or API endpoint, verify:
- **Contract Adherence:** Ensure payload strictly adheres to [`docs/API_CONTRACT.md`](API_CONTRACT.md) and [`docs/AI_CONTRACT.md`](AI_CONTRACT.md).
- **Coordinate Standard:** Interchanged coordinates must use GeoJSON `[longitude, latitude]` format (EPSG:4326).
- **Timestamp Standard:** All timestamps must use ISO-8601 with explicit timezone offsets (e.g., `2026-08-29T18:42:11+05:30`).
- **Identifier Stability:** All entities (`segment_id`, `event_id`, `bus_id`, `incident_id`) must use deterministic, unique string IDs.
- **Nullability & Defaults:** Optional fields (`heading_deg`, `evidence_uri`, `plate_text`) must be nullable without breaking schema deserialization.
- **Evidence Formatting:** Media references must be fully qualified HTTPS URLs or valid storage paths, not unbounded Base64 strings.
- **Known Discrepancies:** Consult [`docs/BUGS_AND_DISCREPANCIES.md`](BUGS_AND_DISCREPANCIES.md) for active interface alignment tasks.
