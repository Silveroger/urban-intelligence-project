# SIH 26124 — AI-Powered Mobile Urban Intelligence Platform

Decision-support GIS dashboard and edge perception system converting public transport fleet telemetry and computer vision detections into persistent, aggregate road health and traffic intelligence.

---

## Quickstart

### 1. Frontend Dashboard (`src/`)
```bash
# Install dependencies
npm install

# Start local Vite development server
npm run dev
```
The dashboard runs at `http://localhost:5173`.

### 2. Backend & Spatial Server (`backend/`)
```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Start FastAPI server
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger API docs: `http://localhost:8000/docs`.

### 3. Edge AI Live Scanner (`ai/`)
```bash
# Run real-time desktop perception scanner on sample bus feed
python run_live_scanner.py
```

### 4. Database Verification (`scripts/`)
```bash
# Verify Supabase tables and RLS policies
node scripts/verify_supabase.cjs
```

---

## Documentation Index

All project documentation follows a single-owner hierarchy:

- **Agent Context:** [`AGENT_CONTEXT.md`](AGENT_CONTEXT.md)
- **Product Requirements (PRD):** [`docs/PRD.md`](docs/PRD.md)
- **Technology Stack:** [`docs/TECH_STACK.md`](docs/TECH_STACK.md)
- **System Architecture:** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- **Frontend Architecture:** [`docs/FRONTEND_ARCHITECTURE.md`](docs/FRONTEND_ARCHITECTURE.md)
- **API Contract:** [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md)
- **AI Perception Contract:** [`docs/AI_CONTRACT.md`](docs/AI_CONTRACT.md)
- **Database Schema (PostGIS & Supabase):** [`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md)
- **Module Ownership:** [`docs/MODULE_OWNERSHIP.md`](docs/MODULE_OWNERSHIP.md)
- **Architectural Decisions (ADRs):** [`docs/DECISIONS.md`](docs/DECISIONS.md)
- **Current State:** [`docs/AGENT_STATE.md`](docs/AGENT_STATE.md)
- **Backlog:** [`docs/BACKLOG.md`](docs/BACKLOG.md)
- **Environment & Setup:** [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md)
- **Security:** [`docs/SECURITY.md`](docs/SECURITY.md)
- **Testing Strategy:** [`docs/TESTING.md`](docs/TESTING.md)

---

## Available Scripts

- `npm run dev`: Launch Vite development server with HMR.
- `npm run build`: Typecheck with `tsc -b` and compile production bundle.
- `npm run lint`: Run ESLint across project files.
- `npm run preview`: Preview production build locally.
