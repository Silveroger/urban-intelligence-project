# Development Environment Setup

## 1. Prerequisites
- **Node.js:** v18.0.0+ (v20+ LTS recommended)
- **Package Manager:** `npm` (bundled with Node.js)
- **Python:** v3.10 to v3.14
- **Google Maps Platform Account:** With Maps JavaScript API enabled and a Vector Map ID configured.
- **Supabase Account:** PostgreSQL database instance with PostGIS installed in the `gis` schema.

---

## 2. Zero-Friction Local Development (Recommended)

Launch both the Backend and Frontend with a single command from the repository root (`urban-dashboard/`):

```powershell
.\start-dev.ps1
```

This automated launcher:
1. Spawns the **FastAPI Backend** in a dedicated window at [http://localhost:8000](http://localhost:8000).
2. Spawns the **React GIS Dashboard** in a dedicated window at [http://localhost:5173](http://localhost:5173).
3. Automatically launches the live dashboard in your default browser.

### Verification Endpoints:
- **Dashboard:** [http://localhost:5173](http://localhost:5173)
- **API Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **System Health:** [http://localhost:8000/health](http://localhost:8000/health)
- **Database & PostGIS Health:** [http://localhost:8000/health/database](http://localhost:8000/health/database)

---

## 3. Dedicated Subsystem Launchers

If you prefer launching subsystems individually:

### Backend Launcher (`urban-dashboard/`)
```powershell
.\start-backend.ps1
```
*(Or on cmd.exe: `.\start-backend.bat`)*

Or run manually with Python:
```bash
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Launcher (`urban-dashboard/`)
```powershell
.\start-frontend.ps1
```
*(Or on cmd.exe: `.\start-frontend.bat`)*

Or run manually with npm:
```bash
npm run dev
```

---

## 4. Environment Variables Configuration

### 4.1 Frontend Environment (`.env` in repository root)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `VITE_GOOGLE_MAPS_API_KEY` | Yes | — | Google Maps JavaScript API key with vector map access. |
| `VITE_GOOGLE_MAPS_MAP_ID` | Yes | — | Google Cloud Vector Map ID for 3D vector rendering & Advanced Markers. |
| `VITE_API_BASE_URL` | Yes | `http://localhost:8000` | Base URL for FastAPI backend REST endpoints. |
| `VITE_USE_MOCK` | Yes | `false` | When `false` (default for live deployment), connects to FastAPI backend and Supabase PostGIS. When `true`, uses local fixtures in `src/data/` for offline development. |

### 4.2 Backend Environment (`backend/.env`)
Copy `backend/.env.example` to `backend/.env`:
```bash
cd backend
cp .env.example .env
```

`backend/app/core/config.py` automatically resolves `backend/.env` regardless of whether the process is launched from `urban-dashboard/` or `backend/`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `ENVIRONMENT` | Yes | `development` | Deployment environment name. |
| `PORT` | Yes | `8000` | Port for the FastAPI server. |
| `HOST` | Yes | `0.0.0.0` | Host binding for Uvicorn. |
| `SUPABASE_URL` | Yes | — | Supabase project URL (`https://[REF].supabase.co`). |
| `SUPABASE_ANON_KEY` | Yes | — | Public anonymous API key. |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | — | Administrative service role key (backend only). |
| `SUPABASE_STORAGE_BUCKET` | Yes | `road-evidence` | Private Supabase Storage bucket for defect and incident media. |
| `DATABASE_URL` | Yes | — | Async PostgreSQL connection string with regional pooler. |
| `POSTGIS_SCHEMA` | Yes | `gis` | Schema hosting PostGIS functions (`gis`). |
| `MAP_MATCH_MAX_DISTANCE_METERS`| No | `25.0` | Distance threshold in meters for snapping GPS observations to road centerlines. |
| `CONFIDENCE_THRESHOLD` | No | `0.50` | Minimum confidence score ($0.0-1.0$) to confirm AI observations. |
| `CORS_ORIGINS` | No | `http://localhost:5173,http://localhost:3000` | Permitted frontend origins. |

> [!IMPORTANT]
> **Supabase Regional IPv4 Session Pooler Requirement (Windows / IPv4 Networks):**
> Direct Supabase database hostnames (`db.<project-ref>.supabase.co`) resolve exclusively via IPv6 (AAAA) records in AWS regions. On Windows or environments without IPv6 routing, connections fail with `[Errno 11001] getaddrinfo failed`.
> Always use the regional IPv4 Session Pooler host in `DATABASE_URL` (e.g., `postgresql+asyncpg://postgres.[project-ref]:[PASS]@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres`).

---

## 5. Testing & Verification

Run the full automated test suite:
```bash
pytest -v
```
All **47 automated unit, API, schema, AI integration, and live database integration tests** should pass (100% pass rate).

Verify frontend typecheck and build:
```bash
npm run build
```
Should compile cleanly with zero TypeScript errors.
