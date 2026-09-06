# Development Environment Setup

## 1. Prerequisites
- **Node.js:** v18.0.0+ (v20+ LTS recommended)
- **Package Manager:** `npm` (bundled with Node.js)
- **Python:** v3.10 to v3.14
- **Google Maps Platform Account:** With Maps JavaScript API enabled and a Vector Map ID configured.
- **Supabase Account:** PostgreSQL database instance with PostGIS installed in the `gis` schema.

---

## 2. Frontend Setup (`urban-dashboard`)

1. **Install Dependencies:**
   ```bash
   npm install
   ```

2. **Configure Environment Variables:**
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

3. **Start Development Server:**
   ```bash
   npm run dev
   ```
   The application runs at `http://localhost:5173`.

### Frontend Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `VITE_GOOGLE_MAPS_API_KEY` | Yes | — | Google Maps JavaScript API key with vector map access. |
| `VITE_GOOGLE_MAPS_MAP_ID` | Yes | — | Google Cloud Vector Map ID for 3D vector rendering & Advanced Markers. |
| `VITE_API_BASE_URL` | Yes | `http://localhost:8000` | Base URL for FastAPI backend REST endpoints. |
| `VITE_USE_MOCK` | Yes | `false` | When `false` (default for live deployment), connects to FastAPI backend and Supabase PostGIS. When `true`, uses local fixtures in `src/data/` for offline development. |

---

## 3. Backend Setup (`backend/`)

1. **Create and Activate Virtual Environment:**
   ```bash
   cd backend
   python -m venv .venv

   # On Windows (PowerShell):
   .venv\Scripts\Activate.ps1

   # On macOS/Linux:
   source .venv/bin/activate
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Backend Environment Variables:**
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   > [!IMPORTANT]
   > **Supabase Regional IPv4 Session Pooler Requirement (Windows / IPv4 Networks):**
   > Direct Supabase database hostnames (`db.<project-ref>.supabase.co`) resolve exclusively via IPv6 (AAAA) records in AWS regions. On Windows or environments without IPv6 routing, connections fail with `[Errno 11001] getaddrinfo failed`.
   > Always use the regional IPv4 Session Pooler host in `DATABASE_URL` (e.g., `postgresql+asyncpg://postgres.[project-ref]:[PASS]@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres`).

4. **Run Database Migration and Schema Reconciliation:**
   a. In the Supabase SQL Editor, execute [`backend/scripts/migrate_to_documented_schema.sql`](../backend/scripts/migrate_to_documented_schema.sql) to provision canonical tables (`routes`, `trips`) and the non-destructive compatibility view `gps_records`.
   b. Run the legacy constraint cleanup script to safely drop superseded NOT NULL constraints while preserving historical rows:
   ```bash
   python scripts/drop_legacy_notnull.py
   ```
   c. Seed the database with OSM-derived canonical Chandigarh road network, buses, defect observations, and incidents:
   ```bash
   python scripts/seed_chandigarh_demo.py
   ```

5. **Verify Database Connectivity & Run Automated Tests:**
   ```bash
   python scripts/test_connection.py
   pytest -v
   ```
   All 40 automated unit, API, schema, and live integration tests should pass (100%).

6. **Start Backend Server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   - OpenAPI Docs: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`
   - Health Check: `http://localhost:8000/health`
   - Database Health Check: `http://localhost:8000/health/database`

### Backend Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ENVIRONMENT` | Yes | `development` | Deployment environment (`development`, `production`). |
| `PORT` | Yes | `8000` | HTTP and WebSocket server port. |
| `HOST` | Yes | `0.0.0.0` | Server host binding. |
| `DATABASE_URL` | Yes | — | Async PostgreSQL connection string (`postgresql+asyncpg://...`). |
| `POSTGIS_SCHEMA` | Yes | `gis` | PostgreSQL schema where PostGIS extension is installed. |
| `SUPABASE_URL` | Yes | — | Supabase project URL. |
| `SUPABASE_ANON_KEY` | Yes | — | Supabase public anonymous API key. |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | — | Supabase service role key (backend server only). |
| `SUPABASE_STORAGE_BUCKET` | Yes | `road-evidence` | Supabase Storage bucket for defect and incident media. |
| `MAP_MATCH_MAX_DISTANCE_METERS`| No | `25.0` | Maximum search radius for snapping GPS points to road segments. |
| `CONFIDENCE_THRESHOLD` | No | `0.50` | Minimum confidence score to confirm and score observations. |
| `CORS_ORIGINS` | Yes | `http://localhost:5173` | Comma-separated allowed frontend origins. |

---

## 4. Key Security Rules
- **Never commit `.env`:** Keep `.env` strictly in `.gitignore` in both root and `backend/`.
- **API Key Restrictions:** Configure HTTP referrer restrictions in Google Cloud Console (`localhost:5173/*` and production domains).
- **Service Role Key:** The `SUPABASE_SERVICE_ROLE_KEY` has administrative access and must never be exposed to frontend builds or client code.
