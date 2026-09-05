# Project Backlog & Planned Work

## 1. P0 — Immediate Integration Tasks

### Completed Backend P0 Baseline (Commit `873553f`)
- [x] **FastAPI Backend Scaffold:** Async server setup with CORS, lifespan management, and custom exception handling.
- [x] **Database & PostGIS Integration:** SQLAlchemy 2.0 Async + asyncpg models and queries qualified in `gis` schema.
- [x] **REST Endpoints:** Complete API suite for road segments, defect events, traffic incidents, fleet buses, and telemetry.
- [x] **WebSocket Live Stream:** Real-time `/ws/live` endpoint broadcasting `BUS_TELEMETRY` and `NEW_EVENT` frames.
- [x] **Spatial Engines:** PostGIS map-matching (`ST_DWithin`) and deterministic road health scoring engine.
- [x] **Evidence Media:** Supabase Storage integration with signed URL generation.
- [x] **Schema Reconciliation Migration:** Production-grade transactional script (`backend/scripts/migrate_to_documented_schema.sql`).
- [x] **Backend Test Suite:** Unit, route, coordinates, scoring, and websocket test cases with in-memory fixtures.

### Active P0 Integration Tasks
- [ ] **Execute Schema Reconciliation:** Run `migrate_to_documented_schema.sql` in Supabase SQL Editor to align live database with canonical schema.
- [ ] **Fix Frontend Segments Response Ingestion:** Update `src/services/api.ts` to parse GeoJSON `FeatureCollection` or request `?format=flat` ([BUG-001](BUGS_AND_DISCREPANCIES.md#bug-001-get-apiv1segmentsgeojson-response-shape-mismatch)).
- [ ] **Align Incident Severity Model:** Add `severity` ($1-4$) and `severity_label` to `src/types/incidents.ts` and `IncidentInspector.tsx` ([BUG-002](BUGS_AND_DISCREPANCIES.md#bug-002-incident-metric-discrepancy-incident_score-vs-severity)).
- [ ] **Connect Frontend WebSocket Client:** Wire `src/services/websocket.ts` to `Dashboard.tsx` to animate live fleet buses and render live event markers ([BUG-004](BUGS_AND_DISCREPANCIES.md#bug-004-frontend-websocket-client-disconnected-from-ui-state)).
- [ ] **WebSocket Reconnection & Resilience:** Implement auto-reconnection with exponential backoff and ping heartbeats ([BUG-010](BUGS_AND_DISCREPANCIES.md#bug-010-missing-websocket-auto-reconnection--backoff-in-frontend)).

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
