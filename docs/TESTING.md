# Testing Strategy & Procedures

## 1. Testing Strategy Overview
Quality assurance is enforced across five distinct layers to ensure UI reliability, strict contract adherence, backend calculation correctness, and spatial precision:

```text
┌────────────────────────────────────────────────────────┐
│  Layer 1: Frontend Static Analysis & Build             │
│  (ESLint, Strict TypeScript, tsc -b, Vite build)       │
├────────────────────────────────────────────────────────┤
│  Layer 2: Backend Unit, Route & AI Integration Tests   │
│  (pytest, Scoring Formula, Severity, Backend Adapter)  │
├────────────────────────────────────────────────────────┤
│  Layer 3: Spatial & Coordinate Verification            │
│  (GeoJSON [lng, lat] vs Google {lat, lng}, PostGIS)    │
├────────────────────────────────────────────────────────┤
│  Layer 4: Diagnostic Connectivity & Ingestion Scripts  │
│  (test_connection.py, test_ingestion.py)               │
├────────────────────────────────────────────────────────┤
│  Layer 5: End-to-End Integration & Visual Verification │
│  (Live Dashboard, Inspector Drawers, WebSocket)        │
└────────────────────────────────────────────────────────┘
```

---

## 2. Verification Commands & Verified Results

### 2.1 Frontend Checks (from project root)

| Target | Command | Result & Purpose |
|---|---|---|
| **Linter** | `npm run lint` | Passes with zero errors. Verifies React hook dependency rules and styling standards. |
| **Typecheck & Build** | `npm run build` | **Clean build in 1.67s (exit code 0)**. Executes `tsc -b` (project reference build) followed by `vite build` to ensure zero compilation or type errors. |
| **Development Preview** | `npm run preview` | Spins up a local production build server for realistic performance testing. |

### 2.2 Backend Checks (from `backend/` or repository root via `.venv`)

| Target | Command | Result & Purpose |
|---|---|---|
| **Full Test Suite** | `pytest -v` | **47/47 passed in 29.75s (100% pass rate)** across unit, schema, scoring, routes, analytics, AI adapter, and live integration tests. |
| **AI Integration Tests** | `pytest tests/test_ai_integration.py` | Validates `BackendIngestAdapter`, schema normalization, OCR enforcement, AI diagnostic metadata preservation, video endpoints, and real-time WebSocket dispatch. |
| **Real DB Integration** | `pytest tests/test_integration_real.py` | Validates live connection to PostgreSQL 17.6 via pooler, PostGIS in `gis` schema, all 9 canonical entities/views, and real map matching. |
| **Scoring & Recovery** | `pytest tests/test_scoring.py` | Verifies deterministic health scoring, confidence penalty weighting (`weight_by_confidence=True`), and clean-pass recovery credits. |
| **Coordinates & Geometry**| `pytest tests/test_coordinates.py` | Validates latitude/longitude bounding boxes and GeoJSON transformations. |
| **API Route Tests** | `pytest tests/test_api_routes.py` | Tests REST endpoints, canonical bus model serialization, analytics summary, and SQL-level severity filtering. |
| **WebSocket Test** | `pytest tests/test_websocket.py` | Tests WebSocket connection manager, client lifecycle, ping/pong heartbeat, and dead-connection cleanup. |
| **Database Diagnostics** | `python scripts/test_connection.py` | Verifies pooler connectivity, PostGIS 3.3.7 in `gis` schema, canonical entities/views, and storage bucket. |
| **End-to-End Simulation** | `python scripts/test_ingestion.py` | Executes 6-stage end-to-end ingestion pipeline simulation against the running server. |
| **Fleet Simulation** | `python scripts/simulate_chandigarh_buses.py` | Simulates live transit buses traveling along canonical OSM corridors, posting to `/api/v1/telemetry`. |

---

## 3. Specialized Testing Procedures

### 3.1 AI Adapter Integration Verification (`tests/test_ai_integration.py`)
- **Schema Normalization:** Tests that raw edge dictionaries from YOLO detectors are converted to valid Pydantic models.
- **Taxonomy Mapping:** Verifies that `event_type="pedestrian"` is mapped to `incident` with `class_name="vulnerable_pedestrian"`.
- **OCR Rule Enforcement:** Verifies that `plate_text` without `plate_confidence` triggers a 422 validation failure.
- **Diagnostic Metrics Preservation:** Verifies that AI civil metrics (`risk_score`, `breadth_cm`, `depth_cm`, `dimensions`, `risk_assessment`) are stored into `observations.metadata` JSONB.
- **Video Router Integration:** Validates `/api/v1/ingest/video/status` and `/api/v1/ingest/video/process` routers.
- **Live WebSocket Dispatch:** Confirms `NEW_EVENT` frames contain normalized payloads.

### 3.2 Live PostgreSQL & PostGIS Verification (`tests/test_integration_real.py`)
- **Connection Route:** Connects to Supabase Regional IPv4 Session Pooler (port 5432) with `search_path=public,gis`.
- **PostGIS Spatial Check:** Executes distance calculation (`gis.ST_Distance`) with `gis.geography` casting on coordinates in Chandigarh.
- **Canonical Schema Parity:** Asserts that all 9 canonical entities/views exist in `public`: `buses`, `gps_points`, `road_segments`, `observations`, `incidents`, `segment_history`, `routes`, `trips`, `gps_records`.
- **View Parity:** Verifies that row count in `gps_records` equals row count in `gps_points`.

### 3.3 Ingestion Pipeline 6-Stage Simulation (`scripts/test_ingestion.py`)
1. **Stage 0 (Health):** Validates `/health` and `/health/database`.
2. **Stage 1 (Telemetry):** Posts GPS trace to `/api/v1/telemetry`, asserts HTTP 201 and position persistence in `buses` & `gps_points`.
3. **Stage 2 (OCR Rule):** Posts observation with `plate_text` but no `plate_confidence`, asserts HTTP 422 `VALIDATION_ERROR`.
4. **Stage 3 (Quarantine):** Posts observation with `confidence = 0.35` (< 0.50), asserts HTTP 201 with `quarantined = true` and `status = 'quarantined'`.
5. **Stage 4 (Confirmed Observation):** Posts confirmed observation (`confidence = 0.92`), asserts HTTP 201, map-matching, and score update.
6. **Stage 5 (GeoJSON Export):** Fetches `/api/v1/segments/geojson`, asserts valid `FeatureCollection` returned.
7. **Stage 6 (WebSocket):** Connects to `/ws/live`, sends `"ping"`, asserts `{"type": "PONG"}` received.

### 3.4 Live Health & Endpoint Verification
- `GET /health` $\to$ `HTTP 200 {"status": "ok", "environment": "development"}`
- `GET /health/database` $\to$ `HTTP 200 {"status": "connected", "postgis_version": "POSTGIS=\"3.3.7...\"", "tables_found": [...]}`
- `GET /api/v1/segments/geojson` $\to$ HTTP 200 with 11 canonical OSM road features
- `GET /api/v1/events` $\to$ HTTP 200 with validated defect events
- `GET /api/v1/incidents` $\to$ HTTP 200 with incidents and severity labels
- `GET /api/v1/buses` $\to$ HTTP 200 with active bus fleet
- `GET /api/v1/analytics/summary` $\to$ HTTP 200 with citywide KPIs
- `GET /api/v1/ingest/video/status` $\to$ HTTP 200 with video scanning progress
- `WSS /ws/live` $\to$ real-time `BUS_TELEMETRY`, `NEW_EVENT`, `NEW_INCIDENT`, `SEGMENT_UPDATE`, and heartbeat `PONG`

---

## 4. Definition of Done
A feature or bugfix is complete only after:
1. `npm run lint` passes with zero errors.
2. `npm run build` compiles with zero TypeScript errors.
3. Backend tests pass (`pytest` exits with code 0, 47/47 tests passing).
4. Live health checks (`/health` and `/health/database`) return HTTP 200.
5. Relevant interactive workflows (clicking segments, toggling filters, opening inspectors) are verified in the browser.
6. Documentation and contracts are updated if interfaces changed.
