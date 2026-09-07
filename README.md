# SIH 26124 — AI-Powered Mobile Urban Intelligence Platform

Decision-support GIS dashboard and geospatial intelligence backend converting public transport fleet telemetry and edge computer vision detections into persistent, aggregate road health and traffic intelligence.

---

## Zero-Friction Quickstart

Launch the entire end-to-end development environment with a single command from the repository root:

```powershell
.\start-dev.ps1
```

This automated launcher will:
1. Start the **Canonical FastAPI Backend** in a dedicated window at [http://localhost:8000](http://localhost:8000).
2. Start the **GIS Urban Dashboard Frontend** in a dedicated window at [http://localhost:5173](http://localhost:5173).
3. Wait for port binding and automatically open the live dashboard in your default web browser.

### Verification Endpoints:
- **Urban Dashboard:** [http://localhost:5173](http://localhost:5173)
- **API Interactive Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **System Health:** [http://localhost:8000/health](http://localhost:8000/health)
- **Database & PostGIS Health:** [http://localhost:8000/health/database](http://localhost:8000/health/database)

---

## Standalone Subsystem Launchers

If you prefer starting subsystems individually:

### 1. Canonical Backend (`backend/`)
From repository root:
```powershell
.\start-backend.ps1
```
*(Or on cmd.exe: `.\start-backend.bat`)*

Or manually with Python:
```bash
python -m uvicorn backend.app.main:app --reload --port 8000 --host 0.0.0.0
```

### 2. Frontend Dashboard (`src/`)
From repository root:
```powershell
.\start-frontend.ps1
```
*(Or on cmd.exe: `.\start-frontend.bat`)*

Or manually with npm:
```bash
npm run dev
```

### 3. Edge AI Perception & Hardware Receiver (`ai/`)
To stream live AI inference or receive hardware telemetry into the canonical backend:
```bash
# Run real-time edge scanner with local video
python run_live_scanner.py --post-backend

# Run UDP telemetry receiver for edge hardware (ESP32/GPS)
python run_hardware_receiver.py --backend http://localhost:8000
```

---

## Integrated Architecture

```text
BUS CAMERA / GPS / HARDWARE
        │
        ▼
CHIRAG AI / EDGE PERCEPTION (ai/)
  - Road defect detector (potholes, cracks, waterlogging)
  - Infrastructure detector (dividers, zebra crossings, signs)
  - Traffic density detector (counts, density index)
  - Pedestrian detector (vulnerable pedestrians)
  - License plate OCR & confidence scoring
  - Vehicle tracker (ByteTrack, erratic driving)
  - Edge bandwidth optimizer & hardware receiver
        │
        ▼
BackendIngestAdapter (ai/adapter/backend_adapter.py)
  - Normalizes edge taxonomy to canonical schemas
  - Preserves diagnostic metrics in PostgreSQL observations.metadata JSONB
        │
        ▼
CANONICAL FASTAPI BACKEND (backend/)
        │
        ├─► PostgreSQL 17.6 + PostGIS 3.3.7 (gis schema)
        ├─► Road map matching (ST_DWithin / ST_Distance)
        ├─► Multi-pass condition score aggregation (0-100)
        ├─► Incident persistence & Supabase Storage signed URLs
        └─► Real-time WebSocket live broadcasting (/ws/live)
        │
        ▼
REACT + GOOGLE MAPS + DECK.GL DASHBOARD (src/)
  - Live vector polylines with OSM-derived canonical geometries
  - Advanced Markers for buses and traffic incidents
  - High-performance deck.gl heatmap overlays
  - Real-time WebSocket streaming with auto-reconnect backoff
```

---

## Documentation Index

All project documentation follows a single-owner authoritative hierarchy:

- **Agent Context:** [`AGENT_CONTEXT.md`](AGENT_CONTEXT.md)
- **Product Requirements (PRD):** [`docs/PRD.md`](docs/PRD.md)
- **Technology Stack:** [`docs/TECH_STACK.md`](docs/TECH_STACK.md)
- **System Architecture:** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- **Frontend Architecture:** [`docs/FRONTEND_ARCHITECTURE.md`](docs/FRONTEND_ARCHITECTURE.md)
- **API Contract:** [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md)
- **AI Perception Contract:** [`docs/AI_CONTRACT.md`](docs/AI_CONTRACT.md)
- **Database Schema (PostGIS):** [`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md)
- **Module Ownership:** [`docs/MODULE_OWNERSHIP.md`](docs/MODULE_OWNERSHIP.md)
- **Architectural Decisions (ADRs):** [`docs/DECISIONS.md`](docs/DECISIONS.md)
- **Current State:** [`docs/AGENT_STATE.md`](docs/AGENT_STATE.md)
- **Backlog:** [`docs/BACKLOG.md`](docs/BACKLOG.md)
- **Environment & Setup:** [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md)
- **Security:** [`docs/SECURITY.md`](docs/SECURITY.md)
- **Testing Strategy:** [`docs/TESTING.md`](docs/TESTING.md)
- **Defects & Discrepancies Register:** [`docs/BUGS_AND_DISCREPANCIES.md`](docs/BUGS_AND_DISCREPANCIES.md)

---

## Available Scripts

### Frontend Scripts
- `npm run dev`: Launch Vite development server with HMR.
- `npm run build`: Typecheck with `tsc -b` and compile production bundle with zero errors.
- `npm run lint`: Run ESLint across project files.
- `npm run preview`: Preview production build locally.

### Backend Scripts (inside `backend/` or from root via `.venv`)
- `pytest -v`: Run complete test suite (**47/47 tests passing, 100% pass rate**, covering unit, routes, schema, AI integration, and live PostgreSQL + PostGIS integration).
- `python scripts/test_connection.py`: Test PostGIS connectivity in `gis` schema, verify all 9 canonical entities/views, and check storage bucket.
- `python scripts/test_ingestion.py`: Execute 6-stage end-to-end edge AI observation ingestion simulation.
- `python scripts/seed_chandigarh_demo.py`: Seed database with OSM-derived canonical Chandigarh road network (`chandigarh_roads_canonical.geojson`), buses, events, and incidents.
- `python scripts/simulate_chandigarh_buses.py`: Simulate live fleet buses traveling along canonical road corridors and streaming GPS coordinates to `/api/v1/telemetry`.
- `python scripts/drop_legacy_notnull.py`: Idempotently drop superseded legacy NOT NULL constraints across database tables.
