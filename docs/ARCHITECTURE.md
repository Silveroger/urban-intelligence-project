# System Architecture

## 1. Architectural Overview
The SIH 26124 platform is a distributed geospatial intelligence system that converts continuous edge camera streams, GPS tracking, and hardware telemetry into persistent, aggregate road health and traffic intelligence visualized on a decision-support dashboard.

```text
BUS CAMERA / GPS / HARDWARE
        │
        ▼
CHIRAG AI / EDGE PERCEPTION (ai/)
  - Specialized Computer Vision Detectors (YOLOv8)
  - Potholes, Cracks, Surface Defects, Waterlogging
  - Road Dividers, Zebra Crossings, Signboards
  - Vehicle Classification, Traffic Density Estimation
  - Vulnerable Pedestrian Detection
  - License Plate OCR Localization & Confidence
  - ByteTrack Multi-Object Tracking & Erratic Driving
  - GPS/Video Frame Timestamp Synchronization
  - Edge Bandwidth Optimizer & Evidence Packager
  - Hardware UDP Receiver (ESP32 / GPS / IMU)
        │
        ▼
BackendIngestAdapter (ai/adapter/backend_adapter.py)
  - Translates raw edge inference to canonical schemas
  - Normalizes edge taxonomy (e.g. pedestrian -> incident)
  - Enforces OCR plate confidence validation rules
  - Preserves diagnostic metrics in PostgreSQL metadata JSONB
        │
        ▼
CANONICAL FASTAPI BACKEND (backend/)
  - REST Ingestion APIs:
      POST /api/v1/telemetry    (GPS Trace Ingestion)
      POST /api/v1/observations (AI Defect Ingestion)
      POST /api/v1/incidents    (Traffic Violations)
  - Core Services:
      app/services/ingestion.py    (Validation & Quarantine)
      app/services/map_matching.py (PostGIS Spatial Snapping)
      app/services/scoring.py      (Deterministic Road Scoring)
      app/services/aggregation.py  (Multi-pass Aggregation)
      app/services/evidence.py     (Supabase Storage 1hr Signed URLs)
  - Real-Time WebSocket Broadcaster (/ws/live):
      BUS_TELEMETRY, NEW_EVENT, NEW_INCIDENT, SEGMENT_UPDATE
  - HTTP 503 Database Error Gateway (Zero SQLite Fallback)
        │
        ▼
GEOSPATIAL PROCESSING & PERSISTENCE (Supabase Cloud)
  - PostgreSQL 17.6 + PostGIS 3.3.7 (gis schema)
  - Regional IPv4 Session Pooler (search_path: public, gis)
  - OSM-Derived Canonical Road Geometries (EPSG:4326)
  - Authoritative Physical Table: gps_points
  - Compatibility View: gps_records (maps over gps_points)
  - Tables: buses, routes, trips, road_segments, observations,
            incidents, segment_history
  - GiST Spatial Indexing on all geometry columns
        │
        ▼
REACT + GOOGLE MAPS + DECK.GL DASHBOARD (src/)
  - React 19 + TypeScript + Vite + Tailwind CSS
  - Google Maps Vector API (Map ID) + Advanced Markers
  - OSM Canonical Road Polylines (WGS84 EPSG:4326)
  - deck.gl High-Performance Aggregate Heatmap Overlays
  - Single Coordinate Boundary: geoJsonToGooglePath([lng, lat] -> {lat, lng})
  - Real-Time Streaming: /ws/live with auto-reconnect backoff
  - Segment, Event, and Incident Inspection Drawers
  - Civil Hazard Diagnostics & Bounding Evidence Inspector
```

---

## 2. Subsystem Ownership & Boundaries

### 2.1 Chirag / Edge AI Perception Subsystem (`ai/`)
- **Responsibilities:** Onboard edge computer vision executing on dashcam video and hardware sensors.
- **Preserved Algorithms & Components:**
  - `ai/detectors/road_defect_detector.py`: Detects potholes, surface cracks, damaged pavement, and waterlogging. Preserved with civil hazard metrics (`risk_score`, `breadth_cm`, `depth_cm`, `dimensions`, `risk_assessment`).
  - `ai/detectors/infrastructure_detector.py`: Detects missing zebra crossings, road dividers, and damaged/missing traffic signs.
  - `ai/detectors/traffic_density_detector.py`: Multi-class vehicle classification (`car`, `bus`, `truck`, `motorcycle`, `auto_rickshaw`), vehicle counting, and density index estimation.
  - `ai/detectors/pedestrian_detector.py`: Detects vulnerable pedestrians and school children crossing in active roadways.
  - `ai/detectors/plate_recognizer.py`: License plate localization and OCR text recognition with associated confidence scores.
  - `ai/tracker/vehicle_tracker.py`: SORT/ByteTrack multi-object tracking and rash driving / erratic weaving detection.
  - `ai/telemetry/gps_sync.py`: Frame-to-GPS coordinate and timestamp synchronization.
  - `ai/edge_optimizer.py`: 95% edge bandwidth reduction transmitting structured JSON observation events + cropped bounding box keyframes.
  - `ai/hardware_receiver.py`: UDP telemetry listener receiving live ESP32/GPS and camera telemetry.
  - `ai/test_video_generator.py`: Synthetic test video and GPS track generator for offline validation.
  - `ai/pipeline.py`: Master Edge AI pipeline orchestrating video frame processing and detection dispatch.
- **Critical Policy:** All detector algorithms and ML models were **preserved rather than rewritten**.

### 2.2 Integration Boundary: `BackendIngestAdapter` (`ai/adapter/backend_adapter.py`)
- **Responsibilities:** Acts as the single, thin translation boundary between edge perception outputs and canonical Backend REST APIs.
- **Key Operations:**
  - **Taxonomy Normalization:** Maps edge `event_type="pedestrian"` to canonical `event_type="incident"` with `class_name="vulnerable_pedestrian"`.
  - **Coordinate Translation:** Normalizes `lat`/`lng` keys to canonical `latitude`/`longitude` and GeoJSON `[longitude, latitude]`.
  - **OCR Rule Enforcement:** Enforces that detected `plate_text` is strictly accompanied by `plate_confidence`.
  - **AI Diagnostics Preservation:** Packs AI civil engineering metrics (`risk_score`, `risk_level`, `breadth_cm`, `depth_cm`, `dimensions`, `risk_assessment`) into `metadata_json`, persisted in PostgreSQL `observations.metadata` JSONB.
  - **Target Endpoints:**
    - `POST /api/v1/telemetry`: Vehicle GPS telemetry.
    - `POST /api/v1/observations`: Defect detections and hazard observations.
    - `POST /api/v1/incidents`: Traffic violations and safety incidents.

### 2.3 Eshan / Canonical Backend Subsystem (`backend/`)
- **Responsibilities:** Ingestion validation, spatial road-network map matching, multi-pass observation aggregation, dynamic condition scoring ($0-100$), confidence estimation, clean-pass recovery, historical state maintenance, Supabase Storage evidence management, and WebSocket streaming.
- **Connectivity:** Uses Supabase Regional IPv4 Session Pooler on port 5432 with `connect_args={"server_settings": {"search_path": "public, gis"}}`. Eliminates silent SQLite fallback, routing database connection errors to HTTP 503 `DATABASE_CONNECTION_ERROR`.
- **Core Implemented Modules:**
  - `app/services/ingestion.py`: Validates perception payloads, enforces OCR plate confidence rules, quarantines low-confidence observations ($< 0.50$, stored with `status = 'quarantined'`, HTTP 201), map-matches confirmed detections, updates road score, and broadcasts `NEW_EVENT`.
  - `app/services/map_matching.py`: Executes spatial snapping to nearest road segment using PostGIS `gis.ST_DWithin` and `gis.ST_Distance`.
  - `app/services/scoring.py`: Computes deterministic road condition scores ($0-100$) with repeat-defect multipliers, confidence penalty scaling (`weight_by_confidence=True`), and clean-pass recovery credits (+5.0 condition points per clean pass).
  - `app/services/aggregation.py`: Recalculates segment metrics (`pothole_count`, `waterlogging_count`, `observation_count`), debounces history snapshot insertion to 10-second intervals (BUG-006 resolution), and broadcasts `SEGMENT_UPDATE` frames (BUG-017 resolution).
  - `app/services/telemetry.py`: Ingests vehicle GPS points into authoritative `gps_points` table, updates latest bus position, and broadcasts `BUS_TELEMETRY` frames.
  - `app/services/incidents.py`: Manages traffic violations and obstructions, generates signed evidence URLs, and broadcasts `NEW_INCIDENT` frames (BUG-016 resolution).
  - `app/services/evidence.py`: Integrates with Supabase Storage (`road-evidence` bucket) to store defect crops and dynamically generates 1-hour signed URLs.
  - `app/api/v1/analytics.py`: Computes aggregate citywide infrastructure KPIs.
  - `app/websocket/manager.py`: Broadcast connection manager distributing live frames (`BUS_TELEMETRY`, `NEW_EVENT`, `NEW_INCIDENT`, `SEGMENT_UPDATE`) with dead connection pruning and heartbeat ping/pong handling.
  - `app/api/v1/video.py`: Router triggering edge video perception scanning (`/api/v1/ingest/video/status`, `/api/v1/ingest/video/process`).
- **Persistence & GPS Architecture:**
  - `gps_points` is the authoritative physical table for raw telemetry.
  - `gps_records` is a permanent compatibility VIEW over `gps_points`. Do NOT create competing GPS pipelines.
  - 9 reconciled canonical entities: `buses`, `routes`, `trips`, `road_segments`, `gps_points`, `gps_records` (view), `observations`, `incidents`, `segment_history`. See [`docs/DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md).

### 2.4 Discarded / Replaced Duplicate Components
During the integration, duplicate and incompatible components from the earlier ML branch were **permanently discarded** rather than merged into production:
1. **In-Memory Observation Storage:** Discarded. Replaced by PostgreSQL + PostGIS persistent tables.
2. **Duplicate Spatial Engine:** Discarded. Replaced by canonical PostGIS spatial functions in schema `gis` (`ST_DWithin`, `ST_Distance`).
3. **Duplicate Road Aggregation:** Discarded. Replaced by canonical `app/services/aggregation.py` and `app/services/scoring.py`.
4. **Duplicate WebSocket Hub:** Discarded. Replaced by canonical `app/websocket/manager.py` broadcasting on `/ws/live`.
5. **Direct Supabase GPS Pipeline:** Discarded. Replaced by canonical `/api/v1/telemetry` writing to `gps_points`.
6. **Obsolete ML Ingest Endpoints:** Discarded. Replaced by canonical REST routes (`/api/v1/observations`, `/api/v1/telemetry`, `/api/v1/incidents`).

**Rationale:** The Canonical Backend is the sole authoritative owner of persistence, map matching, aggregation, and WebSocket client communication.

### 2.5 Canonical Road Geometry Pipeline (OSM-Derived)
- **Canonical Source of Truth:** Authentic road centerlines extracted from OpenStreetMap (OSM) for Chandigarh's primary arterial corridors (Jan Marg, Madhya Marg, Dakshin Marg, Purv Marg, Vigyan Marg, Sarovar Path, Himalaya Marg, Sukhna Path, Udyog Path, and Vidya Path).
- **Persistent Asset:** Permanently versioned in [`backend/data/chandigarh_roads_canonical.geojson`](../backend/data/chandigarh_roads_canonical.geojson) and loaded into `public.road_segments.geom` in PostGIS.
- **Coordinate Standard:** WGS84 (EPSG:4326) with 13 to 38 vertices per segment, capturing genuine road curvatures and intersections.
- **Spatial Alignment:** Fleet bus simulation paths (`simulate_chandigarh_buses.py`), AI defect observations, and traffic incidents are snapped to and traverse along these canonical coordinates with verified $0.00\,\text{m}$ spatial offset.

### 2.6 GIS Frontend Dashboard (`src/`)
- **Responsibilities:** Hardware-accelerated map visualization, colored road segment polylines, Advanced Markers, deck.gl density heatmaps, filter state management, analytics charts, and drill-down inspection drawers.
- **Live Configuration:** Operates with `VITE_USE_MOCK=false` against the FastAPI backend, with real-time WebSocket deltas updating moving buses and segment degradation colors without full-page reloads.
- **Edge AI Video Processing Hub:** Integrated modal (`VideoProcessingHub.tsx`) allowing operators to trigger edge video perception scanning directly from the dashboard and monitor real-time progress.

---

## 3. Integration Architecture & Data Flow

### 3.1 Data Flow Patterns
1. **Edge Perception & Telemetry Capture:** Cameras and GPS units stream frames to `ai/pipeline.py` or `ai/hardware_receiver.py`. Detectors flag road defects, hazards, traffic bottlenecks, and plate numbers.
2. **Adapter Normalization:** `BackendIngestAdapter` normalizes payloads, packs diagnostic metrics into `metadata_json`, and dispatches HTTP POST requests to the canonical backend.
3. **Backend Ingestion & PostGIS Map-Matching:** The backend validates schemas, quarantines low-confidence events, snaps confirmed events to road segments using `gis.ST_DWithin`, recomputes segment health scores, updates `road_segments`, debounces `segment_history`, and generates 1-hour signed URLs for evidence.
4. **Real-Time WebSocket Streaming:** The backend broadcasts delta frames over `/ws/live` (`BUS_TELEMETRY`, `NEW_EVENT`, `NEW_INCIDENT`, `SEGMENT_UPDATE`).
5. **Initial State Hydration:** When a client opens the dashboard, it issues asynchronous REST requests (`/api/v1/segments/geojson`, `/api/v1/events`, `/api/v1/incidents`, `/api/v1/buses`, `/api/v1/analytics/summary`) to populate the map viewport, summary cards, and inspector drawers.
6. **Graceful Degradation:** If WebSocket drops, the frontend automatically reconnects with exponential backoff (1s to 30s) while maintaining full operational capability using hydrated REST state.
