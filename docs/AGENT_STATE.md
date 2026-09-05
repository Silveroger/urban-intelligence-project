# Agent & Implementation State

> **Note:** This document tracks temporary, current development state. Stale entries are pruned upon milestone completion.

## 1. Current Implementation Baseline
- **Frontend Dashboard (`src/`):** P0 MVP complete (Google Maps vector rendering, colored road polylines, Advanced Markers for defect/incident events, bus markers, filter sidebar, KPI cards, segment/event/incident inspector drawers, historical degradation charts).
- **Heatmap Layer:** Phase 1 deck.gl GPU heatmap overlay implemented and functional via `@deck.gl/google-maps`.
- **Data Mode:** Standalone mock data mode operational (`VITE_USE_MOCK=true`) in `src/services/api.ts`.
- **FastAPI Backend v1 (`backend/`):**
  - High-performance asynchronous FastAPI server (`app/main.py`) with CORS, structured exception handlers, and life cycle management.
  - SQLAlchemy 2.0 Async + asyncpg + GeoAlchemy2 models mapping to the 6 core entities (`road_segments`, `observations`, `incidents`, `segment_history`, `buses`, `gps_points`).
  - Full REST API suite (`/api/v1/segments`, `/api/v1/events`, `/api/v1/incidents`, `/api/v1/telemetry`, `/api/v1/buses`, `/api/v1/observations`).
  - WebSocket live broadcaster (`/ws/live`) with connection manager for real-time `BUS_TELEMETRY` and `NEW_EVENT` frames.
  - Map-matching service querying PostGIS in `gis` schema with `ST_DWithin` and `ST_Distance`.
  - Deterministic road health scoring engine with repeat-defect penalty multipliers.
  - Supabase Storage integration with signed URLs for defect crop frames and incident media.
  - Production-grade schema reconciliation migration script (`backend/scripts/migrate_to_documented_schema.sql`).
  - Test suite with unit and route tests in `backend/tests/`.
- **Type Safety & Build:** Strict TypeScript validation enabled; clean ESLint status; zero compiler errors (`npm run build` passing).

---

## 2. Active Milestones & Focus
- **Current Milestone:** Frontend-Backend Integration & Database Schema Reconciliation.
- **Active Tasks:**
  - **Execute Schema Migration:** Run [`backend/scripts/migrate_to_documented_schema.sql`](../backend/scripts/migrate_to_documented_schema.sql) in Supabase SQL Editor to align existing database tables with canonical contracts (resolves BUG-003).
  - **Fix Frontend Road Segments Ingestion:** Update `src/services/api.ts` to parse GeoJSON FeatureCollection or append `?format=flat` (resolves BUG-001).
  - **Synchronize Incident Severity Model:** Update `src/types/incidents.ts` and `IncidentInspector.tsx` to display numeric severity (1-4) alongside `severity_label` (resolves BUG-002).
  - **Connect Live WebSocket Updates:** Implement `useLiveStream` or WebSocket listener in `Dashboard.tsx` to consume `/ws/live` events and animate moving buses (resolves BUG-004).
  - **Validate End-to-End Edge Ingestion:** Run `backend/scripts/test_ingestion.py` against live PostGIS instance to verify full edge detection $\to$ road scoring pipeline.

---

## 3. Known Blockers & Dependencies
- **Database Schema Migration Execution:** The live Supabase database requires running `migrate_to_documented_schema.sql` before live REST requests will succeed against canonical column names.
- **Google Maps API Key:** Ensure valid Vector Map ID is configured in `.env` for hardware-accelerated 3D vector map features.
- **Bug Register:** All identified cross-subsystem defects and discrepancies are cataloged in [`docs/BUGS_AND_DISCREPANCIES.md`](BUGS_AND_DISCREPANCIES.md).

---

## 4. Architectural Decision References
- All architectural decisions are formally documented in [`docs/DECISIONS.md`](DECISIONS.md).
