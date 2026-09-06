# Project Backlog & Planned Work

## 1. P0 — Immediate Integration Tasks

### Completed Backend Recovery, Integration & Canonical Geometry Tasks
- [x] **Regional IPv4 Pooler Connectivity:** Resolved Windows IPv6 DNS failure (`[Errno 11001] getaddrinfo failed`) via Supabase Regional IPv4 Session Pooler (port 5432).
- [x] **Schema Reconciliation Execution:** Executed `migrate_to_documented_schema.sql` on live Supabase database with zero data loss, establishing 9 canonical entities and compatibility views.
- [x] **Legacy Constraint Migration:** Executed `scripts/drop_legacy_notnull.py` to remove superseded NOT NULL constraints on legacy columns and add `observations.status`.
- [x] **Authoritative GPS Architecture:** Enforced `gps_points` as physical table and `gps_records` as compatibility view.
- [x] **Driver Hardening & HTTP 503 Gateway:** Eliminated silent SQLite fallback; implemented custom exception handlers mapping database errors to HTTP 503 `DATABASE_CONNECTION_ERROR`.
- [x] **Confidence Scoring & Clean-Pass Recovery:** Implemented confidence penalty scaling (`weight_by_confidence=True`) and clean-pass recovery (+5.0 condition points per clean pass).
- [x] **History Snapshot Debouncing:** Implemented 10-second history snapshot debouncing in `aggregation.py` (resolves BUG-006).
- [x] **WebSocket Live Stream Expansion:** Added broadcasts for `NEW_INCIDENT` (resolves BUG-016) and `SEGMENT_UPDATE` (resolves BUG-017) alongside `BUS_TELEMETRY` and `NEW_EVENT`.
- [x] **Dynamic Signed Evidence URLs:** Implemented 1-hour signed URLs for Supabase Storage (`road-evidence` bucket) upon API response serialization (resolves BUG-007).
- [x] **Comprehensive Test Suite:** 40/40 passing tests (100% pass rate) across unit, scoring, validation, routes, analytics, and live PostgreSQL/PostGIS integration tests (`tests/test_integration_real.py`).
- [x] **End-to-End Simulation:** Verified 6-stage telemetry and observation ingestion simulation against running server (`scripts/test_ingestion.py`).
- [x] **Chandigarh Canonical Seed Data Generation:** Generated OpenStreetMap-derived canonical road centerlines (`backend/data/chandigarh_roads_canonical.geojson`), seeded PostGIS `road_segments.geom`, and aligned bus routes/GPS traces.
- [x] **Fix Frontend Segments Response Ingestion:** Updated `src/services/api.ts` to parse GeoJSON `FeatureCollection` and flat formats ([BUG-001](BUGS_AND_DISCREPANCIES.md#bug-001-get-apiv1segmentsgeojson-response-shape-mismatch)).
- [x] **Align Incident Severity Model:** Added `severity` ($1-4$), `severity_label`, and `incident_score` to `src/types/incidents.ts`, `IncidentInspector.tsx`, and backend schemas ([BUG-002](BUGS_AND_DISCREPANCIES.md#bug-002-incident-metric-discrepancy-incident_score-vs-severity)).
- [x] **Connect Frontend WebSocket Client:** Connected `src/services/websocket.ts` to `Dashboard.tsx` to animate live fleet buses, prepend live events/incidents, and update segment degradation colors ([BUG-004](BUGS_AND_DISCREPANCIES.md#bug-004-frontend-websocket-client-disconnected-from-ui-state)).
- [x] **WebSocket Reconnection & Resilience:** Implemented auto-reconnection with exponential backoff (1s-30s) and ping heartbeats in `src/services/websocket.ts` ([BUG-010](BUGS_AND_DISCREPANCIES.md#bug-010-missing-websocket-auto-reconnection--backoff-in-frontend)).
- [x] **OSM Canonical Road Geometry Fix:** Replaced coarse synthetic straight lines with OSM-derived canonical geometries containing 13 to 38 vertices per segment, aligned visually with Google Maps basemap ([BUG-024](BUGS_AND_DISCREPANCIES.md#bug-024-coarse-synthetic-road-geometries-cutting-across-chandigarh-grid)).

---

## 2. P1 — Advanced Dashboard Features
- [ ] **Trip Replay & Time Scrubber:** Add interactive time slider to scrub through historical bus runs and observe defect progression over 24-hour / 7-day windows.
- [ ] **Evidence Media Inspection Modal:** Add high-resolution image viewer with zoom/pan capabilities for pothole crops and defect bounding boxes.
- [ ] **Maintenance Priority Ranking Tool:** Build a dedicated view sorting city segments by defect density, condition degradation rate, and traffic load.
- [ ] **Work-Order Export:** Implement PDF/CSV/GeoJSON export of repair work orders with GPS coordinates and evidence links.
- [ ] **Fleet Sensing Coverage Analytics:** Add coverage heatmap showing city road segments traversed by buses in the last 24/48 hours.

---

## 3. P2 — Future Extensions
- [ ] **Missing Infrastructure Reasoning:** Map visualization for missing zebra crossings, faded lane markings, and damaged road signage.
- [ ] **Route Delay & Congestion Analysis:** Correlate road defects with bus schedule deviations and transit corridor travel times.
- [ ] **Origin-Destination Flow Modeling:** Visualize aggregated commuter flow matrices across municipal sectors.
