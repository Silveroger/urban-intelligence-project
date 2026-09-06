# SIH 26124 — AI-Powered Mobile Urban Intelligence Platform

Decision-support GIS dashboard and geospatial intelligence backend converting public transport fleet telemetry and computer vision detections into persistent, aggregate road health and traffic intelligence.

---

## Quickstart

### 1. Frontend Dashboard (`src/`)

```bash
# 1. Install dependencies
npm install

# 2. Copy environment file
cp .env.example .env

# 3. Start local development server
npm run dev
```

The frontend application runs at `http://localhost:5173`.

### 2. FastAPI Backend (`backend/`)

```bash
cd backend

# 1. Create and activate virtual environment
python -m venv .venv
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy environment file and configure Supabase Session Pooler
cp .env.example .env
# Ensure DATABASE_URL uses the Supabase IPv4 Regional Session Pooler (port 5432 or 6543)
# e.g.: postgresql+asyncpg://postgres:[PASSWORD]@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres

# 4. Start local backend server
uvicorn app.main:app --reload --port 8000
```

- API Documentation (Swagger): `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- System Health: `http://localhost:8000/health`
- Database & PostGIS Health: `http://localhost:8000/health/database`

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
- `npm run build`: Typecheck with `tsc -b` and compile production bundle.
- `npm run lint`: Run ESLint across project files.
- `npm run preview`: Preview production build locally.

### Backend Scripts (inside `backend/`)
- `pytest -v`: Run complete test suite (40/40 tests passing, 100% pass rate, including live PostgreSQL 17.6 + PostGIS 3.3.7 integration tests).
- `python scripts/test_connection.py`: Test PostGIS connectivity in `gis` schema, verify all 9 canonical entities/views, and check storage bucket.
- `python scripts/test_ingestion.py`: Execute 6-stage end-to-end edge AI observation ingestion simulation.
- `python scripts/seed_chandigarh_demo.py`: Seed database with OSM-derived canonical Chandigarh road network (`chandigarh_roads_canonical.geojson`), buses, events, and incidents.
- `python scripts/simulate_chandigarh_buses.py`: Simulate live fleet buses traveling along canonical road corridors and streaming GPS coordinates to `/api/v1/telemetry`.
- `python scripts/drop_legacy_notnull.py`: Idempotently drop superseded legacy NOT NULL constraints across database tables.
