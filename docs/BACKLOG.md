# Project Backlog & Planned Work

## 1. P0 — Immediate Integration Tasks (COMPLETED)

### Completed Integration & Architecture Tasks:
- [x] **Regional IPv4 Pooler Connectivity:** Resolved Windows IPv6 DNS failure (`[Errno 11001] getaddrinfo failed`) via Supabase Regional IPv4 Session Pooler (port 5432).
- [x] **Schema Reconciliation Execution:** Executed `migrate_to_documented_schema.sql` on live Supabase database with zero data loss, establishing 9 canonical entities and compatibility views.
- [x] **Legacy Constraint Migration:** Executed `scripts/drop_legacy_notnull.py` to remove superseded NOT NULL constraints on legacy columns and add `observations.status`.
- [x] **Authoritative GPS Architecture:** Enforced `gps_points` as physical table and `gps_records` as compatibility view.
- [x] **Driver Hardening & HTTP 503 Gateway:** Eliminated silent SQLite fallback; implemented custom exception handlers mapping database errors to HTTP 503 `DATABASE_CONNECTION_ERROR`.
- [x] **Confidence Scoring & Clean-Pass Recovery:** Implemented confidence penalty scaling (`weight_by_confidence=True`) and clean-pass recovery (+5.0 condition points per clean pass).
- [x] **History Snapshot Debouncing:** Implemented 10-second history snapshot debouncing in `aggregation.py` (resolves BUG-006).
- [x] **WebSocket Live Stream Expansion:** Added broadcasts for `NEW_INCIDENT` (resolves BUG-016) and `SEGMENT_UPDATE` (resolves BUG-017) alongside `BUS_TELEMETRY` and `NEW_EVENT`.
- [x] **Dynamic Signed Evidence URLs:** Implemented 1-hour signed URLs for Supabase Storage (`road-evidence` bucket) upon API response serialization (resolves BUG-007).
- [x] **OSM Canonical Road Geometry Fix:** Replaced coarse synthetic straight lines with OSM-derived canonical geometries containing 13 to 38 vertices per segment, aligned visually with Google Maps basemap (`chandigarh_roads_canonical.geojson`).
- [x] **Frontend WebSocket Integration:** Connected `src/services/websocket.ts` to `Dashboard.tsx` to animate live fleet buses, prepend live events/incidents, and update segment degradation colors with auto-reconnect backoff.
- [x] **Edge AI Subsystem Integration:** Integrated Chirag's computer vision detectors (`road_defect_detector.py`, `infrastructure_detector.py`, `traffic_density_detector.py`, `pedestrian_detector.py`, `plate_recognizer.py`), vehicle tracker (`vehicle_tracker.py`), GPS sync (`gps_sync.py`), optimizer (`edge_optimizer.py`), and hardware receiver (`hardware_receiver.py`).
- [x] **Thin Boundary Adapter:** Implemented `ai/adapter/backend_adapter.py` (`BackendIngestAdapter`) normalizing taxonomy (`pedestrian` $\to$ `incident` with `class_name="vulnerable_pedestrian"`), validating OCR confidence, and preserving AI diagnostic metrics in PostgreSQL `observations.metadata` JSONB.
- [x] **Elimination of Duplicate ML Backend:** Discarded duplicate in-memory observation stores, duplicate spatial engine, duplicate aggregation, and duplicate WebSocket hub. Standardized on canonical FastAPI Backend + PostGIS as single source of truth.
- [x] **Zero-Friction Local Development Launchers:** Created `start-dev.ps1` (orchestrating backend, frontend, and browser launch), `start-backend.ps1`, `start-frontend.ps1`, and Windows batch alternatives.
- [x] **Environment & Import Bootstrap:** Added `sys.path` bootstrapping in `backend/__init__.py` and `backend/app/main.py` enabling root execution; configured `.vscode/settings.json` and synced system Python.
- [x] **Comprehensive Test Suite:** **47/47 tests passing (100% pass rate)** in ~30s covering unit, scoring, routes, AI integration, and live PostGIS integration; clean frontend build (`npm run build`).

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
