# Agent & Implementation State

> **Note:** This document tracks temporary, current development state. Stale entries are pruned upon milestone completion.

## 1. Current Implementation Baseline
- **Edge AI & Computer Vision Subsystem (`ai/`):** Complete OpenCV + YOLO edge perception engine for road defects (potholes, damaged roads, waterlogging), infrastructure deficiencies (missing dividers, zebra crossings, signboards), traffic density estimation, vulnerable pedestrian crossing detection, vehicle tracking, and license plate OCR with confidence scoring.
- **Backend & Spatial Ingestion (`backend/`):** Complete FastAPI server with PostGIS-compatible spatial map-matching engine, dynamic condition scoring, real-time WebSocket live feed (`/ws/live`), evidence crop server, and video ingestion triggers.
- **Frontend Dashboard (`src/`):** Interactive GIS command center with Google Maps vector rendering, Advanced Markers, deck.gl overlays, KPI cards, inspector drawers, and the new Edge AI Video & Hardware Ingestion Hub.
- **Data Modes:** Fully operational across both Live Backend (`VITE_USE_MOCK=false`) and Standalone Mock mode (`VITE_USE_MOCK=true`).

---

## 2. Active Milestones & Focus
- **Current Milestone:** Complete SIH 26124 Edge AI + Backend + Dashboard Integration verified.
- **Active Tasks:**
  - Ready for physical hardware video and GPS field data ingestion.
  - End-to-end synthetic verification passed with 0 errors.

---

## 3. Known Blockers & Dependencies
- **Live Backend Availability:** Backend PostGIS instance currently in parallel development (Butar). Frontend continues using typed mock fixtures.
- **Google Maps API Key:** Ensure valid Vector Map ID is configured in `.env` for hardware-accelerated 3D vector map features.

---

## 4. Architectural Decision References
- All architectural decisions are formally documented in [DECISIONS.md](file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/DECISIONS.md).
