# Testing Strategy & Procedures

## 1. Testing Strategy Overview
Quality assurance is enforced across five distinct layers to ensure UI reliability, strict contract adherence, backend calculation correctness, and spatial precision:

```text
┌────────────────────────────────────────────────────────┐
│  Layer 1: Frontend Static Analysis & Build             │
│  (ESLint, Strict TypeScript, tsc -b, Vite build)       │
├────────────────────────────────────────────────────────┤
│  Layer 2: Backend Unit & Contract Tests                │
│  (pytest, Scoring Formula, Severity, Validation)       │
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

## 2. Verification Commands

### 2.1 Frontend Checks (from project root)

| Target | Command | Purpose |
|---|---|---|
| **Linter** | `npm run lint` | Verifies code styling, unused variables, and React hook dependency rules. |
| **Typecheck & Build** | `npm run build` | Executes `tsc -b` (project reference build) followed by `vite build` to ensure zero compilation or type errors. |
| **Development Preview** | `npm run preview` | Spins up a local production build server for realistic performance testing. |

### 2.2 Backend Checks (from `backend/` directory)

| Target | Command | Purpose |
|---|---|---|
| **Full Test Suite** | `pytest -v` | Runs complete test suite — **40/40 passed (100% pass rate)** across unit, schema, scoring, routes, analytics, and live integration tests. |
| **Real DB Integration** | `pytest tests/test_integration_real.py` | Validates live connection to PostgreSQL 17.6 via pooler, PostGIS in `gis` schema, all 9 canonical entities/views, and real map matching. |
| **Scoring & Recovery** | `pytest tests/test_scoring.py` | Verifies deterministic health scoring, confidence penalty weighting (`weight_by_confidence=True`), and clean-pass recovery credits. |
| **Coordinates & Geometry**| `pytest tests/test_coordinates.py` | Validates latitude/longitude bounding boxes and GeoJSON transformations. |
| **API Route Tests** | `pytest tests/test_api_routes.py` | Tests REST endpoints, canonical bus model serialization, analytics summary, and SQL-level severity filtering. |
| **WebSocket Test** | `pytest tests/test_websocket.py` | Tests WebSocket connection manager, client lifecycle, ping/pong heartbeat, and dead-connection cleanup. |
| **Database Diagnostics** | `python scripts/test_connection.py` | Verifies pooler connectivity, PostGIS 3.3.7 in `gis` schema, canonical entities/views, and storage bucket. |
| **End-to-End Simulation** | `python scripts/test_ingestion.py` | Executes 6-stage end-to-end ingestion pipeline simulation against the running server. |
| **Fleet Simulation** | `python scripts/simulate_chandigarh_buses.py` | Simulates live transit buses traveling along canonical OSM corridors, posting to `/api/v1/telemetry`. |
| **Drop Legacy Constraints**| `python scripts/drop_legacy_notnull.py`| Idempotently drops superseded legacy NOT NULL constraints to ensure canonical inserts succeed. |

---

## 3. Specialized Testing Procedures

### 3.1 Live PostgreSQL & PostGIS Verification (`tests/test_integration_real.py`)
- **Connection Route:** Connects to Supabase Regional IPv4 Session Pooler (port 5432) with `search_path=public,gis`.
- **PostGIS Spatial Check:** Executes distance calculation (`gis.ST_Distance`) with `gis.geography` casting on coordinates in Chandigarh.
- **Canonical Schema Parity:** Asserts that all 9 canonical entities/views exist in `public`: `buses`, `gps_points`, `road_segments`, `observations`, `incidents`, `segment_history`, `routes`, `trips`, `gps_records`.
- **View Parity:** Verifies that row count in `gps_records` equals row count in `gps_points`.

### 3.2 Ingestion Pipeline 6-Stage Simulation (`scripts/test_ingestion.py`)
1. **Stage 0 (Health):** Validates `/health` and `/health/database`.
2. **Stage 1 (Telemetry):** Posts GPS trace to `/api/v1/telemetry`, asserts HTTP 201 and position persistence in `buses` & `gps_points`.
3. **Stage 2 (OCR Rule):** Posts observation with `plate_text` but no `plate_confidence`, asserts HTTP 422 `VALIDATION_ERROR`.
4. **Stage 3 (Quarantine):** Posts observation with `confidence = 0.35` (< 0.50), asserts HTTP 201 with `quarantined = true` and `status = 'quarantined'`.
5. **Stage 4 (Confirmed Observation):** Posts confirmed observation (`confidence = 0.92`), asserts HTTP 201, map-matching, and score update.
6. **Stage 5 (GeoJSON Export):** Fetches `/api/v1/segments/geojson`, asserts valid `FeatureCollection` returned.
7. **Stage 6 (WebSocket):** Connects to `/ws/live`, sends `"ping"`, asserts `{"type": "PONG"}` received.

### 3.3 GIS & Coordinate Transformations
- **Coordinate Order:** Verify that coordinate array inputs `[lng, lat]` are converted into `{lat, lng}` objects via `geoJsonToGooglePath` without reversing lat/lng axes.
- **Polyline Integrity:** Verify that road polylines render over actual street corridors without disjointed vertices.
- **Marker Anchors:** Ensure Advanced Marker pins correctly anchor at exact coordinate centroids.

### 3.4 Contract & Fixture Validation
- **Interface Alignment:** Verify that all mock data files in `src/data/` strictly type-check against domain interfaces in `src/types/` (`RoadSegment`, `Event`, `Incident`, `Bus`).
- **Null Safety:** Verify that optional fields (`heading_deg`, `evidence_uri`, `plate_text`) do not cause `TypeError` crashes when null or undefined.
- **Defect Tracking:** Refer to [`docs/BUGS_AND_DISCREPANCIES.md`](BUGS_AND_DISCREPANCIES.md) for resolved and active interface alignments.

### 3.5 Live & Mock Mode Integration
- **Mock Fallback:** Ensure `VITE_USE_MOCK=true` renders all map layers, cards, and charts without network errors.
- **Live Resilience:** Ensure graceful handling (loading skeletons and HTTP 503 error toast) if `VITE_USE_MOCK=false` is set and the backend endpoint is temporarily unreachable.

### 3.6 Canonical Road Geometry & Visual Alignment Verification
- **OSM Road Centerlines:** Verified authentic OSM coordinates across Chandigarh arterial corridors (`backend/data/chandigarh_roads_canonical.geojson`).
- **Visual Basemap Alignment:** Google Maps polyline rendering inspected to verify road lines follow genuine street curves on Google Maps tiles rather than straight sector shortcuts.
- **Fleet Simulator Verification:** `scripts/simulate_chandigarh_buses.py` streams bus GPS coordinates directly along canonical roads. The live dashboard shows buses moving accurately down Chandigarh corridors with valid headings.
- **Endpoint Verification:**
  - `GET /health` $\to$ `{"status": "healthy"}`
  - `GET /health/database` $\to$ `{"status": "connected", "database": "PostgreSQL 17.6", "postgis": "3.3.7"}`
  - `GET /api/v1/segments/geojson` $\to$ 11 canonical features
  - `GET /api/v1/analytics/summary` $\to$ 72.8 average condition score, tier counts
  - `GET /api/v1/events` $\to$ 20 confirmed events
  - `GET /api/v1/incidents` $\to$ 7 incidents with severity 1-4 & severity_label
  - `GET /api/v1/buses` $\to$ 11 active buses
  - `WSS /ws/live` $\to$ real-time `BUS_TELEMETRY`, `NEW_EVENT`, `NEW_INCIDENT`, `SEGMENT_UPDATE`, and heartbeat `PONG`

---

## 4. Definition of Done
A feature or bugfix is complete only after:
1. `npm run lint` passes with zero errors.
2. `npm run build` compiles with zero TypeScript errors.
3. Backend tests pass (`pytest` exits with code 0, 40/40 tests passing).
4. Relevant interactive workflows (clicking segments, toggling filters, opening inspectors) are verified in the browser.
5. Documentation and contracts are updated if interfaces changed.
