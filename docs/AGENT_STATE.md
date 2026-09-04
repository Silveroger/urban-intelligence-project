# Agent & Implementation State

> **Note:** This document tracks temporary, current development state. Stale entries are pruned upon milestone completion.

## 1. Current Implementation Baseline
- **Edge AI & Computer Vision Subsystem (`ai/`):** 
  - Complete OpenCV + YOLO edge perception engine with modular detectors:
    - Road Defects: Potholes, cracks, damaged road surfaces (`ai/detectors/road_defect_detector.py`)
    - Waterlogging: Stagnant water and submerged lane patches
    - Infrastructure: Missing dividers, missing zebra crossings, damaged signboards (`ai/detectors/infrastructure_detector.py`)
    - Traffic Density & Congestion: Vehicle density estimation and clustering (`ai/detectors/traffic_density_detector.py`)
    - Pedestrian Safety: Vulnerable pedestrian crossing alerts (`ai/detectors/pedestrian_detector.py`)
    - Offending Vehicles: Vehicle tracking (`ai/tracker/vehicle_tracker.py`) and OCR license plate recognition (`ai/detectors/plate_recognizer.py`)
  - Edge Optimizer: ONNX Runtime export, FP16/INT8 quantization, TensorRT acceleration (`ai/edge_optimizer.py`).
  - Desktop Live Scanner Window: Interactive popup window for visual inspection and video diagnostics (`run_live_scanner.py`).
- **Backend & Spatial Ingestion (`backend/`):** 
  - FastAPI asynchronous application server (`backend/app/main.py`).
  - Spatial Engine: Map-matching against road centerlines and dynamic condition score aggregation (`backend/app/services/spatial_engine.py`, `aggregation.py`).
  - Real-time WebSocket live feed (`/ws/live`) with connection manager (`websocket_hub.py`).
  - Video Processing Worker: Background processing endpoint (`/api/v1/ingest/video/process`) and status monitor (`/api/v1/ingest/video/status`) with dynamic detector toggles.
  - Evidence File Server: Static mount at `/evidence` for keyframe crops and incident images.
- **Frontend Dashboard (`src/`):** 
  - Interactive GIS command center with Google Maps vector rendering, Advanced Markers, and deck.gl overlays.
  - Edge AI Video & Hardware Ingestion Hub (`src/components/VideoHub/VideoIngestModal.tsx`).
  - Live Detection HUD overlay and Edge Scanner modal (`LiveDetectionOverlay.tsx`, `EdgeScannerModal.tsx`).
  - GPS Pipeline Drawer (`src/components/GpsPipeline/GpsPipelineDrawer.tsx`) for real-time telemetry streaming and validation.
  - Inspector drawers for Road Segments, AI Events, and Incidents (`src/components/Details/`).
  - Dual Data Modes: Live Backend/Supabase (`VITE_USE_MOCK=false`) and Standalone Mock mode (`VITE_USE_MOCK=true`).
- **Database & Cloud Migrations (`supabase/`):**
  - PostgreSQL / PostGIS schemas (`supabase/migrations/20260902_create_gps_records.sql`, `20260904_full_sih_schema.sql`).
  - Tables: `gps_records`, `observations`, `incidents`, `road_segments`.
  - Row Level Security (RLS) policies and `supabase_realtime` publication.
  - Verification scripts in `scripts/verify_supabase.js` and `scripts/verify_supabase.cjs`.

---

## 2. Active Milestones & Focus
- **Current Milestone:** Hardware field deployment preparation and real-world multi-bus GPS / video feed ingestion.
- **Active Tasks:**
  - Ingesting physical dashcam footage and real-time NMEA/GPS receiver stream into edge perception pipeline.
  - Validating multi-pass degradation curves across repeated runs in production environments.

---

## 3. Known Blockers & Dependencies
- **Google Maps API Key:** Ensure valid Vector Map ID is configured in `.env` for hardware-accelerated 3D vector map features.
- **Supabase Connectivity:** Verify `.env` contains valid `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.

---

## 4. Architectural Decision References
- All architectural decisions are formally documented in [DECISIONS.md](DECISIONS.md).
