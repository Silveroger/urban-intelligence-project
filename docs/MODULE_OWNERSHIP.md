# Module Ownership & Team Boundaries

## 1. Ownership Roster

| Subsystem / Area | Lead Owner | Primary Repository Paths | Core Responsibilities |
|---|---|---|---|
| **GIS Frontend / Dashboard** | **Eshan** | `src/`, `public/` | Map rendering, road condition styling, Advanced Markers, deck.gl overlays, filter panel, KPI cards, inspector drawers, Edge Video Hub modal, UI state management. |
| **Canonical Backend & Geospatial Engine** | **Eshan / Aryush** | `backend/` | FastAPI async services, PostGIS spatial indexing (`gis` schema), GPS road map-matching (`ST_DWithin`), multi-pass score aggregation ($0-100$), REST APIs, WebSocket broadcaster (`/ws/live`), Supabase Storage, database migrations, backend test suites. |
| **Edge AI Perception & Hardware Subsystem** | **Chirag** | `ai/` | YOLOv8 inference models, road defect detection (`road_defect_detector.py`), infrastructure verification (`infrastructure_detector.py`), traffic density classification (`traffic_density_detector.py`), pedestrian safety (`pedestrian_detector.py`), license plate OCR (`plate_recognizer.py`), multi-object tracking (`vehicle_tracker.py`), GPS/video synchronization (`gps_sync.py`), edge optimizer (`edge_optimizer.py`), hardware UDP receiver (`hardware_receiver.py`), test video generation (`test_video_generator.py`). |
| **Integration Boundary (Adapter)** | **Integration** | `ai/adapter/` | Thin translation boundary (`BackendIngestAdapter`) translating edge detection dictionaries to canonical backend REST payloads, taxonomy normalization, OCR rule enforcement, and diagnostic metadata packaging into PostgreSQL `observations.metadata` JSONB. |

---

## 2. Boundary & Architectural Directives

1. **AI Perception Boundary:**
   - AI owns computer vision inference, frame-to-GPS synchronization, and hardware telemetry receiving.
   - AI does NOT own persistence, in-memory observation stores, spatial map-matching, or WebSocket broadcasting.
   - All AI inference and telemetry stream to the canonical Backend via `BackendIngestAdapter`.
2. **Canonical Backend Boundary:**
   - Canonical Backend is the **single source of truth** for persistence, road network map-matching, condition score aggregation, and WebSocket streaming.
   - Database schema is owned exclusively by the canonical Backend (`backend/app/models/`, `backend/scripts/`).
   - No duplicate database, spatial engine, aggregation layer, or WebSocket hub should ever be introduced.
3. **Frontend Boundary:**
   - Frontend owns presentation, user interaction, vector map visualization, and inspection drawers.
   - Frontend consumes backend state via REST hydration and live WebSocket deltas; it does not calculate spatial matching or condition scoring algorithms client-side.
4. **Interface Contracts First:**
   - Cross-boundary changes (modifying API endpoints, changing event schemas, altering coordinate formats) require updating [`docs/API_CONTRACT.md`](API_CONTRACT.md) or [`docs/AI_CONTRACT.md`](AI_CONTRACT.md) before altering code.
5. **Defect & Discrepancy Tracking:**
   - All cross-cutting bugs, contract discrepancies, and integration gaps must be tracked in [`docs/BUGS_AND_DISCREPANCIES.md`](BUGS_AND_DISCREPANCIES.md).
