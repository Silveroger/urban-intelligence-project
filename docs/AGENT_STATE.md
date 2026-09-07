# Agent & Implementation State

> **Note:** This document tracks temporary, current development state. Stale entries are pruned upon milestone completion.

## 1. Current Implementation Baseline
- **Branch:** `backend-ml-integration` (integrates Chirag's AI + hardware pipeline with Eshan's canonical Backend).
- **Backend Status:** Canonical PostGIS architecture preserved with **100% test pass rate (47/47 tests passing)**.
- **AI & Edge Perception Subsystem:**
  - Preserved Chirag's detector algorithms (`road_defect_detector.py`, `infrastructure_detector.py`, `traffic_density_detector.py`, `pedestrian_detector.py`, `plate_recognizer.py`), tracker (`vehicle_tracker.py`), GPS sync (`gps_sync.py`), optimizer (`edge_optimizer.py`), and test video generator (`test_video_generator.py`).
  - Implemented thin boundary adapter: `ai/adapter/backend_adapter.py` (`BackendIngestAdapter`) normalizing telemetry, defect observations, and incident alerts.
  - Normalizes edge taxonomy: maps `event_type="pedestrian"` to canonical `event_type="incident"` with `class_name="vulnerable_pedestrian"`.
  - Normalizes coordinates (`lat`/`lng` to `latitude`/`longitude`) and validates plate OCR confidence.
  - Passes diagnostic metrics (`risk_score`, `risk_level`, `breadth_cm`, `depth_cm`, `dimensions`, `risk_assessment`) into `Observation.metadata_json` (PostgreSQL `observations.metadata` JSONB column).
  - Wired `ai/pipeline.py` and `ai/hardware_receiver.py` to stream normalized outputs to canonical backend REST APIs (`/api/v1/observations`, `/api/v1/telemetry`, `/api/v1/incidents`).
  - Added video processing trigger router: `/api/v1/ingest/video/status` and `/api/v1/ingest/video/process`.
- **Frontend Integration:**
  - Added "Edge AI Video Hub" modal button and `VideoProcessingHub` component to `src/pages/Dashboard.tsx` while strictly preserving Eshan's canonical WebSocket listener (`connectLiveStream`).
  - Added Civil Hazard Diagnostic panel, defect dimensions, and keyframe evidence crop to `src/components/Details/Inspector.tsx` while preserving bus inspection and incident score cards.
  - Verified clean TypeScript build via `npm run build`.
- **Live Database & Infrastructure:**
  - PostgreSQL 17.6 + PostGIS 3.3.7 verified in schema `gis` on Supabase.
  - Single source of truth: all map-matching, road condition scoring recalculation, and WebSocket delta broadcasting occur canonically in PostGIS. No duplicate in-memory backend.
- **Testing & Verification:**
  - `pytest`: 47/47 tests passing (100% pass rate), including all 40 canonical backend tests + 7 new AI integration tests (`tests/test_ai_integration.py`).
  - `npm run build`: Clean compilation with zero TypeScript errors.

---

## 2. Active Milestones & Focus
- **Current Milestone:** AI Subsystem Integration & Compatibility Verification.
- **Status:** Complete. Edge perception models, hardware receiver, and test media from `origin/ml` successfully integrated with canonical Backend and PostGIS database via thin adapter boundary.

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
