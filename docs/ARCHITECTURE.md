# System Architecture

## 1. Architectural Overview
The SIH 26124 platform is a distributed geospatial intelligence system that converts continuous edge telemetry and computer vision detections into persistent, aggregate road health and traffic intelligence visualized on a decision-support dashboard.

```text
┌────────────────────────────────────────────────────────┐
│             Mobile Sensing Fleet (Buses)               │
│  [Camera Sensors] + [GPS Receiver] + [Edge Hardware]   │
└───────────────────────────┬────────────────────────────┘
                            │ Video Stream / Frames + GPS Telemetry
                            ▼
┌────────────────────────────────────────────────────────┐
│             Perception & Edge Ingestion                │
│  - Modular Edge AI (Defects, Water, Traffic, Pedestrians)│
│  - FastAPI Ingestion Engine & Background Video Worker  │
│  - Static Evidence Crop Server (/evidence)             │
└─────────────┬────────────────────────────┬─────────────┘
              │ Structured Observations     │ Direct Telemetry Stream
              ▼                            ▼
┌───────────────────────────┐  ┌─────────────────────────┐
│ PostGIS Spatial Engine    │  │ Supabase Realtime Cloud │
│ - Centerline Map Matching │  │ - GPS Records Stream    │
│ - Multi-Pass Condition    │  │ - Instant Broadcast     │
│ - Historical Degradation  │  │ - Row Level Security    │
└─────────────┬─────────────┘  └───────────┬─────────────┘
              │ REST API + WebSocket        │ Supabase Realtime
              └─────────────┬───────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│             GIS Frontend / Urban Dashboard             │
│  - React 19 + TypeScript + Vite + Tailwind CSS         │
│  - Google Maps Vector API (Map ID) + deck.gl Overlay   │
│  - Edge Video Hub, Scanner Modal & GPS Pipeline Drawer │
│  - Segment, Event & Incident Inspector Drawers         │
│  - Historical Degradation Trends & KPI Analytics       │
└────────────────────────────────────────────────────────┘
```

---

## 2. Subsystem Boundaries & Responsibilities

### 2.1 Edge & Telemetry Subsystem (`ai/telemetry/`)
- **Responsibilities:** Continuous video sampling, GPS coordinate capture, NMEA parsing, local frame filtering, metadata packaging, and edge event triggering.
- **Outputs:** Event observation payloads with synchronized timestamps and spatial coordinates.

### 2.2 AI / Perception Subsystem (`ai/detectors/`, `ai/tracker/`)
- **Responsibilities:** Object detection and segmentation for potholes, surface cracks, waterlogging; pedestrian safety analysis; vehicle detection and tracking; OCR on license plates.
- **Constraints:** Outputs structured JSON payloads conforming to [AI_CONTRACT.md](AI_CONTRACT.md). Does not execute directly within the frontend DOM.

### 2.3 Backend & Geospatial Subsystem (`backend/`)
- **Responsibilities:** Ingestion validation, spatial road-network map matching, multi-pass observation aggregation, dynamic condition scoring ($0-100$), confidence estimation, background video processing, historical state maintenance, and REST/WebSocket API delivery.
- **Persistence:** Relational schema and spatial layers in PostgreSQL/PostGIS and Supabase (see [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)).

### 2.4 GIS Frontend Dashboard (`src/`)
- **Responsibilities:** Hardware-accelerated map visualization, colored road segment polylines, Advanced Markers, deck.gl density heatmaps, filter state management, Video Hub modal, GPS Pipeline drawer, analytics charts, and drill-down inspection drawers.
- **Constraints:** Consumes backend data via [API_CONTRACT.md](API_CONTRACT.md) and Supabase client; does not calculate spatial matching or condition scoring algorithms client-side. See [FRONTEND_ARCHITECTURE.md](FRONTEND_ARCHITECTURE.md).

---

## 3. Integration Architecture & Data Flow

### 3.1 Data Flow Patterns
1. **Initial State Hydration (REST):** Upon page load, the frontend issues asynchronous REST requests (`/api/v1/segments/geojson`, `/api/v1/events`, `/api/v1/incidents`, `/api/v1/buses`, `/api/v1/analytics/summary`) to populate the complete map viewport and initial statistics.
2. **Real-Time Streaming (WebSocket & Supabase):** 
   - The frontend connects to `/ws/live` for backend delta updates (bus telemetry, new events, segment score updates).
   - The frontend can also subscribe directly to Supabase Realtime channels (`public:gps_records`, `public:observations`, `public:incidents`) for distributed edge streaming.
3. **Video Processing Trigger:** The frontend Video Hub submits video/GPS tracks or sample runs to `/api/v1/ingest/video/process` with selective detector flags, polling progress via `/api/v1/ingest/video/status` and receiving live detections over WebSocket.
4. **Graceful Degradation:** If the WebSocket connection drops, the frontend maintains full operational capability using REST polling or cached state without crashing the UI.

### 3.2 Integration Checklist & Pre-Flight Verification
Before connecting a new service, edge node, or API endpoint, verify:
- **Contract Adherence:** Ensure payload strictly adheres to [API_CONTRACT.md](API_CONTRACT.md) and [AI_CONTRACT.md](AI_CONTRACT.md).
- **Coordinate Standard:** Interchanged coordinates must use GeoJSON `[longitude, latitude]` format (EPSG:4326).
- **Timestamp Standard:** All timestamps must use ISO-8601 with explicit timezone offsets (e.g., `2026-09-04T18:42:11+05:30`).
- **Identifier Stability:** All entities (`segment_id`, `event_id`, `bus_id`, `incident_id`) must use deterministic, unique string IDs.
- **Nullability & Defaults:** Optional fields (`heading_deg`, `evidence_uri`, `plate_text`, `bbox`) must be nullable without breaking schema deserialization.
- **Evidence Formatting:** Media references must be fully qualified HTTPS URLs or valid storage paths, not unbounded Base64 strings.
- **Integration Fixtures:** Provide mock fixtures matching live shapes in `src/data/` for local verification.
