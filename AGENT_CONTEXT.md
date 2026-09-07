# SIH 26124 — Agent Operating Context

## 1. Executive Purpose & Authority
This document is the authoritative, compact project context and executive briefing for AI agents working in this repository. It provides the essential context, engineering constraints, conventions, and operational directives required before modifying code.

Detailed domain specifications are strictly owned by their designated documents in `docs/` (see Section 6).

---

## 2. Project Mission & Core Philosophy
**Problem:** SIH 26124 — AI-Powered Mobile Urban Intelligence Platform Using Public Transport Fleet.

- **Core Concept:** City buses and sensing vehicles act as mobile sensing units. Dashcam sensors, GPS receivers, and hardware telemetry capture edge data $\to$ specialized computer vision models detect road defects and traffic events $\to$ thin boundary adapter normalizes edge events to canonical schemas $\to$ backend spatial engine matches observations and aggregates repeated passes $\to$ persistent road health state is maintained in PostgreSQL + PostGIS $\to$ visualized on the decision-support GIS dashboard.
- **Key Differentiator:** The platform focuses on **repeated geospatial observations and persistent road health state**, rather than single-image evaluations or generic chatbot interfaces.

---

## 3. Subsystem Ownership & Boundaries

```text
BUS CAMERA / GPS / HARDWARE
        │
        ▼
CHIRAG AI / EDGE PERCEPTION
        │
        ▼
BackendIngestAdapter (ai/adapter/backend_adapter.py)
        │
        ▼
CANONICAL FASTAPI BACKEND (backend/)
        │
        ├─► PostgreSQL / PostGIS (gis schema)
        ├─► Road map matching (ST_DWithin / ST_Distance)
        ├─► Observation aggregation & road condition scoring (0-100)
        ├─► Incident persistence & Supabase Storage signed URLs
        └─► WebSocket /ws/live broadcasting
        │
        ▼
REACT + GOOGLE MAPS + DECK.GL DASHBOARD (src/)
```

### Explicit Ownership Roster:
- **Chirag / AI Subsystem (`ai/`):**
  - **Owns:** Computer vision perception, YOLO models, defect detectors (`road_defect_detector.py`, `infrastructure_detector.py`), traffic analytics (`traffic_density_detector.py`), pedestrian safety (`pedestrian_detector.py`), license plate OCR (`plate_recognizer.py`), multi-object tracking (`vehicle_tracker.py`), GPS/video synchronization (`gps_sync.py`), edge bandwidth optimization (`edge_optimizer.py`), hardware UDP receiver (`hardware_receiver.py`), AI test runners (`run_hardware_receiver.py`, `run_live_scanner.py`), and test video generators.
  - **Preserved Algorithms:** All detectors and inference logic from `origin/ml` are preserved rather than rewritten.
  - **Does NOT Own:** Database persistence, in-memory observation stores, spatial map-matching, aggregation, or WebSocket delivery.
- **Eshan / Canonical Backend Subsystem (`backend/`):**
  - **Owns:** FastAPI asynchronous services, SQLAlchemy async ORM, PostgreSQL database, PostGIS spatial indexing (`gis` schema), road network map matching (`ST_DWithin`), multi-pass condition score aggregation ($0-100$), REST APIs (`/api/v1/*`), WebSocket streaming (`/ws/live`), Supabase Storage evidence integration, canonical database migrations, and backend test suites (47/47 passing tests).
  - **Does NOT Own:** Client-side React rendering or edge computer vision model training.
- **Integration Boundary (`ai/adapter/backend_adapter.py`):**
  - **Owns:** Thin, non-destructive adapter (`BackendIngestAdapter`) translating edge detection dictionaries to canonical backend REST payloads (`POST /api/v1/telemetry`, `POST /api/v1/observations`, `POST /api/v1/incidents`), normalizing taxonomy (`pedestrian` $\to$ `incident` with `class_name="vulnerable_pedestrian"`), validating OCR confidence rules, and preserving diagnostic metrics in PostgreSQL `observations.metadata` JSONB.
- **GIS Frontend Dashboard (`src/`):**
  - **Owns:** React 19 + TypeScript dashboard, Google Maps vector polylines, Advanced Markers, deck.gl heatmap overlays, multi-tier filters, segment/event/incident inspector drawers, historical degradation charts, and responsive UI state.
  - **Does NOT Own:** Model inference, GPS road-matching algorithms, PostGIS spatial indexing, or multi-pass condition score computation. The frontend visualizes the backend's persistent urban state.
- **Full Team Ownership:** Documented in [`docs/MODULE_OWNERSHIP.md`](docs/MODULE_OWNERSHIP.md).

---

## 4. Critical Engineering Conventions & Constraints

1. **Zero-Friction Local Development Setup:**
   - The entire stack is orchestrated from the repository root via `.\start-dev.ps1`.
   - Spawns Backend on `http://localhost:8000`, Frontend on `http://localhost:5173`, and opens the dashboard in the browser.
   - Dedicated launchers available: `.\start-backend.ps1` (or `.\start-backend.bat`) and `.\start-frontend.ps1` (or `.\start-frontend.bat`).
   - Root `.venv` satisfies dependencies across `backend` and `ai`. `sys.path` bootstrapping in `backend/__init__.py` and `backend/app/main.py` enables root-level and nested execution seamlessly.
2. **Discarded Duplicate Architecture (DO NOT RESURRECT):**
   - The old duplicate ML in-memory backend, duplicate spatial engine, duplicate aggregation layer, duplicate WebSocket hub, and direct Supabase GPS pipeline have been permanently discarded and replaced by the canonical Backend.
   - Canonical Backend owns all persistence, map matching, aggregation, and WebSocket streaming.
3. **Coordinate Format Boundary & Canonical Road Geometries:**
   - Spatial data interchange and storage strictly use GeoJSON `[longitude, latitude]` (EPSG:4326).
   - Google Maps JavaScript API requires `{lat, lng}` objects.
   - Transformations are isolated to `src/utils/coordinates.ts` (`geoJsonToGooglePath`).
   - **OSM-Derived Canonical Road Geometries:** `public.road_segments.geom` holds authentic OpenStreetMap-derived road centerlines (`backend/data/chandigarh_roads_canonical.geojson`) containing 13 to 38 vertices per segment. Never replace these canonical geometries with coarse 2-to-4 point synthetic lines. Bus routes, GPS traces, defect observations, and traffic incidents are strictly aligned to these canonical centerlines.
4. **PostgreSQL Connectivity & Supabase IPv4 Pooler:**
   - On Windows or environments without native IPv6 routing, the direct Supabase database hostname (`db.<project-ref>.supabase.co`) causes immediate `[Errno 11001] getaddrinfo failed` errors.
   - All database connectivity MUST use Supabase's regional IPv4 Session Pooler (e.g. `aws-0-ap-northeast-2.pooler.supabase.com:5432`).
   - The SQLAlchemy engine strictly sets `connect_args={"server_settings": {"search_path": f"public, {settings.POSTGIS_SCHEMA}"}}` to resolve PostGIS types and functions seamlessly.
5. **Canonical GPS Architecture (DO NOT FORK PIPELINE):**
   - `gps_points` is the authoritative, physical source-of-truth table holding raw high-frequency telemetry.
   - `gps_records` is a non-destructive, permanent compatibility VIEW over `gps_points` (`CREATE OR REPLACE VIEW gps_records AS SELECT * FROM gps_points;`).
   - Do NOT create a second competing GPS table or separate ingestion pipeline. All telemetry routes through `gps_points`, and queries against `gps_records` resolve identically without overhead.
6. **Driver Hardening & Error Handling:**
   - Silent SQLite fallback has been completely eliminated. `database.py` fails fast at startup if PostgreSQL or `asyncpg` is missing.
   - All database session and query exceptions are captured and returned to clients as standard HTTP 503 `DATABASE_CONNECTION_ERROR` responses without leaking internal connection details or credentials.
7. **Telemetry Speed Constraint:**
   - Vehicle speed is **optional** in prototype telemetry. Bus telemetry requires only `bus_id`, `timestamp`, `latitude`, `longitude`, and optional `heading_deg`.
8. **Data Layer Abstraction & Live Default:**
   - The UI never imports mock data directly into presentation components. All data access occurs via `src/services/api.ts` and `src/services/websocket.ts`.
   - `VITE_USE_MOCK=false` is the default configuration connecting the React dashboard to the live FastAPI backend and Supabase PostGIS. `VITE_USE_MOCK=true` remains available for offline development.
9. **Heatmap Technology:**
   - Google Maps native `HeatmapLayer` is deprecated. Use `@deck.gl/google-maps` and `@deck.gl/aggregation-layers` inside `DeckHeatmapOverlay.tsx`.
10. **OCR Plate Text Validation & Quarantine:**
    - Detected license plate strings must always be accompanied by a `plate_confidence` score (422 validation error if missing).
    - Observations with `confidence < 0.50` are automatically stored with `status = 'quarantined'`, return HTTP 201 (`quarantined: true`), and do NOT trigger road score degradation or live broadcasts.
11. **Scoring Formula & Clean-Pass Recovery:**
    - Defect penalties are confidence-weighted (`penalty = base_weight * freq_multiplier * confidence`).
    - Clean passes (`clean_pass`, `clear_pass`) provide recovery credits (+5.0 condition points per verified clean pass, up to 100.0 max).
    - Historical snapshots in `segment_history` are debounced to a 10-second window to prevent duplicate records.
12. **Evidence Storage & Signed URLs:**
    - Defect crop frames and incident videos are stored in Supabase Storage (`road-evidence` bucket).
    - API endpoints dynamically generate time-limited (1-hour) signed URLs via `get_signed_evidence_url()` upon response serialization.
13. **PostGIS Schema Qualification:**
    - In Supabase, PostGIS spatial functions reside in the `gis` schema. Backend spatial queries and DDL qualify functions with `gis.` or rely on the engine's `search_path: public, gis`.
14. **Database Reconciliation & Schema Stability:**
    - Live database matches canonical entities: `buses`, `routes`, `trips`, `road_segments`, `gps_points`, `gps_records` (view), `observations`, `incidents`, `segment_history`.
    - All 47 backend tests pass (100% pass rate) across unit, routes, schema, and live PostgreSQL + PostGIS integration tests.
15. **Real-Time WebSocket Streaming (`/ws/live`):**
    - The live WebSocket connection streams `BUS_TELEMETRY`, `NEW_EVENT`, `NEW_INCIDENT`, and `SEGMENT_UPDATE` frames. The frontend implements auto-reconnect backoff (1s-30s) and ping/pong heartbeats to maintain continuous connectivity.

---

## 5. Agent Behavioral & Code Style Rules
- **Inspect Before Modifying:** Understand existing files, props, and types before making changes.
- **Smallest Correct Change:** Prefer surgical, minimal edits over broad rewrites. Keep files concise and maintainable.
- **No Inventions:** Do not invent backend endpoints, database fields, or schemas without updating the relevant contract documents.
- **Zero Token Waste:** Do not write redundant boilerplate, duplicate utility functions, or add libraries when existing dependencies suffice.
- **Verification Mandatory:** Always run `npm run lint`, `npm run build`, and `pytest` after changes. Verify that the app remains functional.

---

## 6. Authoritative Documentation Hierarchy

Every category of project information has exactly ONE authoritative document:

| Category | Authoritative Document | Contents & Scope |
|---|---|---|
| **1. Agent Context** | `AGENT_CONTEXT.md` *(this file)* | Executive project briefing, critical constraints, agent operating rules. |
| **2. Product Requirements** | [`docs/PRD.md`](docs/PRD.md) | Problem statement, user personas, P0/P1/P2 feature scope, acceptance criteria, non-goals. |
| **3. Tech Stack** | [`docs/TECH_STACK.md`](docs/TECH_STACK.md) | Libraries, versions, infrastructure, and technology-specific purposes. |
| **4. Architecture** | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | End-to-end data pipeline, subsystem boundaries, integration architecture. |
| **5. API Contract** | [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) | REST endpoints, WebSocket frame formats, JSON schemas, error codes. |
| **6. AI Contract** | [`docs/AI_CONTRACT.md`](docs/AI_CONTRACT.md) | AI perception structured output schemas, defect classes, confidence rules. |
| **7. Database Schema** | [`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md) | PostgreSQL + PostGIS spatial schema, tables, geometry types, spatial indexing. |
| **8. Module Ownership** | [`docs/MODULE_OWNERSHIP.md`](docs/MODULE_OWNERSHIP.md) | Team subsystem ownership, paths, and cross-boundary collaboration policies. |
| **9. Decisions (ADRs)** | [`docs/DECISIONS.md`](docs/DECISIONS.md) | Architectural Decision Records (ADR-001 through ADR-017) and rationale. |
| **10. Agent State** | [`docs/AGENT_STATE.md`](docs/AGENT_STATE.md) | Temporary implementation baseline, active milestones, and known blockers. |
| **11. Backlog** | [`docs/BACKLOG.md`](docs/BACKLOG.md) | Prioritized backlog tasks across P0, P1, and P2 tiers. |
| **12. Environment** | [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) | Local development setup, npm scripts, and environment variable configuration. |
| **13. Security** | [`docs/SECURITY.md`](docs/SECURITY.md) | Security baseline, secrets handling, API key restrictions, CORS, and data privacy. |
| **14. Testing** | [`docs/TESTING.md`](docs/TESTING.md) | Multi-tier testing strategy, verification commands, and Definition of Done. |
| **15. Frontend Architecture** | [`docs/FRONTEND_ARCHITECTURE.md`](docs/FRONTEND_ARCHITECTURE.md) | Directory structure, state separation, map lifecycle, and color threshold rules. |
| **16. Bugs & Discrepancies** | [`docs/BUGS_AND_DISCREPANCIES.md`](docs/BUGS_AND_DISCREPANCIES.md) | Comprehensive defect, discrepancy, and remediation register across all subsystems. |
