# Agent & Implementation State

> **Note:** This document tracks the authoritative, active implementation baseline and system status.

## 1. Current Implementation Baseline
- **Canonical Integrated Branch:** `main` (promoted from verified integration branch `backend-ml-integration`).
- **Integration Baseline Commit:** `782ceef` (`fix(launchers): sanitize PowerShell quotation and script root for zero-friction dev launch`).
- **Current Architecture:** Canonical FastAPI Backend + Chirag Edge AI via `BackendIngestAdapter` + React GIS Dashboard.
- **Backend Status:** Canonical PostGIS architecture preserved with **100% test pass rate (47/47 tests passing)**.

### Subsystem Status & Verified Components:
1. **Edge AI Perception & Hardware (`ai/`):**
   - Preserved Chirag's detector algorithms (`road_defect_detector.py`, `infrastructure_detector.py`, `traffic_density_detector.py`, `pedestrian_detector.py`, `plate_recognizer.py`), tracker (`vehicle_tracker.py`), GPS sync (`gps_sync.py`), optimizer (`edge_optimizer.py`), hardware receiver (`hardware_receiver.py`), and test video generator (`test_video_generator.py`).
   - Active runner scripts: `python run_live_scanner.py --post-backend` and `python run_hardware_receiver.py --backend http://localhost:8000`.
2. **Boundary Adapter (`ai/adapter/backend_adapter.py`):**
   - Normalizes edge taxonomy: maps `event_type="pedestrian"` to canonical `event_type="incident"` with `class_name="vulnerable_pedestrian"`.
   - Normalizes coordinates (`lat`/`lng` to `latitude`/`longitude`) and enforces plate OCR confidence rules.
   - Preserves diagnostic civil metrics (`risk_score`, `risk_level`, `breadth_cm`, `depth_cm`, `dimensions`, `risk_assessment`) in PostgreSQL `observations.metadata` JSONB.
   - Dispatches directly to canonical FastAPI endpoints (`/api/v1/observations`, `/api/v1/telemetry`, `/api/v1/incidents`).
3. **Canonical Backend (`backend/`):**
   - High-performance async FastAPI running on port 8000.
   - Connected to Supabase PostgreSQL 17.6 + PostGIS 3.3.7 (`gis` schema) via IPv4 Regional Session Pooler.
   - Single source of truth for persistence, spatial map matching (`ST_DWithin`), condition score recalculation, and WebSocket live broadcasts (`/ws/live`).
   - Zero SQLite fallback; HTTP 503 `DATABASE_CONNECTION_ERROR` gateway.
   - Root-level launch enabled via `sys.path` bootstrapping in `backend/__init__.py` and `backend/app/main.py`.
4. **GIS Frontend Dashboard (`src/`):**
   - React 19 + TypeScript + deck.gl + Google Maps vector rendering.
   - Live configuration: `VITE_USE_MOCK=false` streaming real-time bus and defect updates.
   - Edge Video Processing Hub modal (`VideoProcessingHub.tsx`) and Civil Hazard Inspector panel (`Inspector.tsx`).
   - Zero TypeScript compilation errors (`npm run build`).
5. **Zero-Friction Local Development:**
   - Single-command orchestration: `.\start-dev.ps1` launches backend, frontend, and browser dashboard.
   - Dedicated scripts: `start-backend.ps1` and `start-frontend.ps1` (with batch scripts).

---

## 2. Testing & Verification Summary

- **Backend Automated Tests:** 47 passed in ~30s (100% pass rate).
  - 40 canonical backend tests (routes, scoring, severity, coordinates, validation, live PostGIS integration).
  - 7 AI integration tests (`tests/test_ai_integration.py`).
- **Frontend Build:** `npm run build` completed in 1.67s with exit code 0.
- **System Health:** `GET /health` $\to$ HTTP 200 `{"status": "ok"}`.
- **Database Health:** `GET /health/database` $\to$ HTTP 200 `{"status": "connected", "postgis_version": "POSTGIS=\"3.3.7...\""}`.
- **AI Imports & Execution:** Verified in root `.venv` and System Python 3.13.

---

## 3. Subsystem Ownership Rules
- **Chirag / AI:** Owns computer vision perception, YOLO models, detectors, tracking, GPS/video synchronization, edge optimization, hardware UDP receiver, and AI runners.
- **Eshan / Canonical Backend:** Owns persistence, PostGIS spatial indexing, road map-matching, aggregation, REST APIs, WebSocket, Supabase Storage, database migrations, and backend test suites.
- **Integration Adapter:** Owns AI $\to$ Backend translation (`BackendIngestAdapter`).
- **Frontend:** Owns presentation, vector maps, deck.gl overlays, filter state, and inspection drawers.
- **Strict Directive:** No duplicate in-memory backend, duplicate spatial engine, or competing GPS table may ever be introduced.

---

## 4. Backlog & Next Steps
- P1: Trip replay time scrubber on the dashboard.
- P1: Work-order export for municipal repair crews.
- P1: Fleet sensing coverage heatmap.
- P2: Missing infrastructure reasoning (zebra crossings, lane markings).
