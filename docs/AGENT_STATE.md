# Agent & Implementation State

> **Note:** This document tracks temporary, current development state. Stale entries are pruned upon milestone completion.

## 1. Current Implementation Baseline
- **Branch:** `backend-recovery` (fully validated, targeted for canonical promotion to `origin/Backend`).
- **Backend Status:** Recovered, hardened, and verified with **100% test pass rate (40/40 tests passing)**.
- **Live Database & Infrastructure:**
  - PostgreSQL 17.6 + PostGIS 3.3.7 verified in schema `gis` on Supabase.
  - Connectivity routed through Supabase Regional IPv4 Session Pooler (port 5432), resolving Windows IPv6 DNS errors (`[Errno 11001]`).
  - Strict `search_path: public, gis` configured in engine `connect_args`.
  - Elimination of SQLite fallback; database exceptions mapped to HTTP 503 `DATABASE_CONNECTION_ERROR`.
- **Authoritative Database Schema (9 Canonical Entities Reconciled):**
  - All 9 entities verified in PostgreSQL: `buses`, `routes`, `trips`, `road_segments`, `gps_points`, `gps_records` (compatibility view), `observations` (with `status`), `incidents`, `segment_history`.
  - **GPS Pipeline:** `gps_points` is the physical source-of-truth table; `gps_records` is a zero-overhead compatibility view.
  - Superseded legacy NOT NULL constraints successfully dropped via `scripts/drop_legacy_notnull.py` with zero data loss.
- **Canonical Road Geometry Pipeline (OSM-Derived):**
  - Canonical Chandigarh arterial road network centerlines derived from OpenStreetMap (OSM) versioned in `backend/data/chandigarh_roads_canonical.geojson`.
  - PostGIS `public.road_segments.geom` updated with 13 to 38 vertices per segment in WGS84 EPSG:4326.
  - Bus routes, GPS traces, defect observations, and traffic incidents snapped to canonical centerlines with $0.00\,\text{m}$ offset.
  - Eliminates coarse synthetic straight lines; road polylines follow genuine physical street curvature on Google Maps basemap.
- **Scoring & Ingestion Engine:**
  - Confidence-weighted defect penalties (`weight_by_confidence=True`).
  - Clean-pass recovery (+5.0 condition points per verified clean pass, up to 100.0 max).
  - 10-second history snapshot debouncing in `aggregation.py` (resolves BUG-006).
  - Strict OCR rule validation (missing `plate_confidence` returns HTTP 422).
  - Low-confidence quarantine (< 0.50 marked `status = 'quarantined'`, HTTP 201, skips scoring/broadcast).
  - Dynamic 1-hour signed URL generation for evidence assets in Supabase Storage (`road-evidence`).
- **Real-Time Streaming (`/ws/live`):**
  - Active broadcast triggers for `BUS_TELEMETRY`, `NEW_EVENT`, `NEW_INCIDENT` (resolves BUG-016), and `SEGMENT_UPDATE` (resolves BUG-017).
  - Heartbeat ping/pong and dead-connection cleanup verified.
  - Frontend auto-reconnect backoff (1s-30s) and 30s ping heartbeats in `src/services/websocket.ts`.
- **Testing & Verification:**
  - `pytest -v`: 40/40 tests passing (100% pass rate), including live PostgreSQL/PostGIS integration tests in `tests/test_integration_real.py` and analytics summary test in `tests/test_api_routes.py`.
  - `npm run build`: Clean compilation with zero TypeScript errors.
  - Live Endpoints Verified: `/health`, `/health/database`, `/api/v1/segments/geojson` (11 features), `/api/v1/events` (20), `/api/v1/incidents` (7), `/api/v1/buses` (11), `/api/v1/analytics/summary` (72.8 avg condition score).
- **Frontend Dashboard (`src/`):** Full live integration operational (`VITE_USE_MOCK=false`). Consumes REST hydration endpoints and live WebSocket stream, updating moving bus markers, defect/incident markers, and segment health colors dynamically.

---

## 2. Active Milestones & Focus
- **Current Milestone:** Finalize Documentation & Promote `backend-recovery` to Canonical `origin/Backend`.
- **Status:** All implementation and verification phases completed. Documentation synchronized across 16 authoritative specifications.

---

## 3. Known Blockers & Dependencies
- **Database Schema Migration:** RESOLVED. Schema migration and constraint cleanup are complete in the live Supabase instance.
- **Database Connectivity:** RESOLVED. Supabase Regional IPv4 pooler configuration verified.
- **Road Geometry Alignment:** RESOLVED. OSM-derived canonical geometries loaded and verified on Google Maps.
- **Google Maps API Key:** Configured in `.env` for 3D vector map features.
- **Bug Register:** All critical defects and remediations are tracked in [`docs/BUGS_AND_DISCREPANCIES.md`](BUGS_AND_DISCREPANCIES.md).

---

## 4. Architectural Decision References
- All architectural decisions are formally documented in [`docs/DECISIONS.md`](DECISIONS.md) (ADR-001 through ADR-015).
