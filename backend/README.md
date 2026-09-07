# SIH 26124: FastAPI Backend for Urban Intelligence Platform

> **AI-Powered Mobile Urban Intelligence Platform Using Public Transport Fleet**  
> Complete FastAPI backend connecting to the **existing Supabase PostgreSQL + PostGIS database** and providing REST and WebSocket APIs for the React GIS dashboard and edge AI perception ingestion via `BackendIngestAdapter`.

---

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Installation & Virtual Environment](#3-installation--virtual-environment)
4. [Environment Variables](#4-environment-variables)
5. [Schema Alignment & Migration](#5-schema-alignment--migration)
6. [PostGIS Configuration (`gis` Schema)](#6-postgis-configuration-gis-schema)
7. [Database Connection & Pooling](#7-database-connection--pooling)
8. [API Reference](#8-api-reference)
9. [WebSocket Protocol (`/ws/live`)](#9-websocket-protocol-wslive)
10. [AI Ingestion Pipeline & Adapter Boundary](#10-ai-ingestion-pipeline--adapter-boundary)
11. [Map Matching Service](#11-map-matching-service)
12. [Road Health Scoring Formula](#12-road-health-scoring-formula)
13. [Aggregation & Longitudinal History](#13-aggregation--longitudinal-history)
14. [Supabase Storage Integration](#14-supabase-storage-integration)
15. [Severity Architecture](#15-severity-architecture)
16. [Error Handling Contract](#16-error-handling-contract)
17. [Running Locally & Launchers](#17-running-locally--launchers)
18. [Diagnostic & Simulation Scripts](#18-diagnostic--simulation-scripts)
19. [Testing Suite](#19-testing-suite)
20. [Frontend Integration](#20-frontend-integration)

---

## 1. Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                           Edge AI Sensing Fleet                         │
│             (Buses with Dashcams, GPS Trackers & Hardware Nodes)        │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Raw Telemetry & Detection Frames
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Chirag Edge AI Perception (ai/)                      │
│   Detectors: Road Defects, Traffic Density, Pedestrians, Plate OCR      │
│   Tracker: ByteTrack / Multi-Object Tracking & Rash Driving Detector    │
│   Optimizer: 95% Bandwidth Reduction & Keyframe Evidence Packager       │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│            BackendIngestAdapter (ai/adapter/backend_adapter.py)         │
│   - Normalizes coordinates ([lng, lat] and lat/lng keys)                │
│   - Normalizes taxonomy (e.g. pedestrian -> incident)                   │
│   - Enforces OCR plate confidence validation rules                      │
│   - Packs AI diagnostic metrics into PostgreSQL metadata JSONB          │
└───────────────────┬─────────────────────────────────┬───────────────────┘
                    │ Telemetry (GPS)                 │ Perception Events
                    ▼                                 ▼
         POST /api/v1/telemetry            POST /api/v1/observations
┌─────────────────────────────────────────────────────────────────────────┐
│                             FastAPI Backend                             │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────────┐  │
│  │   PostGIS (gis)  │  │  Road Health     │  │   Supabase Storage    │  │
│  │   Map Matching   │  │  Scoring Engine  │  │    (road-evidence)    │  │
│  └────────┬─────────┘  └────────┬─────────┘  └───────────┬───────────┘  │
│           │                     │                        │              │
│           ▼                     ▼                        ▼              │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │     Supabase PostgreSQL 17.6 + PostGIS 3.3.7 (public, gis schemas) │  │
│  │   Tables: buses, routes, trips, road_segments, gps_points,        │  │
│  │           observations, incidents, segment_history                │  │
│  │   Compatibility View: gps_records (maps over gps_points)          │  │
│  └──────────────────────────────────┬────────────────────────────────┘  │
│                                     │ WebSocket Live Stream             │
└─────────────────────────────────────┼───────────────────────────────────┘
                                      │ /ws/live (BUS_TELEMETRY, NEW_EVENT,
                                      │           NEW_INCIDENT, SEGMENT_UPDATE)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       React + Vite GIS Dashboard                        │
│            Google Maps Polyline / Marker / Deck.gl Visualizer           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Prerequisites
- **Python:** Version 3.10, 3.11, 3.12, 3.13, or 3.14.
- **Supabase Project:** Existing Supabase PostgreSQL database with PostGIS enabled in the `gis` schema.
- **Storage Bucket:** A private bucket named `road-evidence` configured in Supabase Storage.

---

## 3. Installation & Virtual Environment

The project standardizes on the root virtual environment (`urban-dashboard/.venv`) for zero-friction execution across both `backend` and `ai`.

From the project root:
```powershell
# Activate root virtualenv on Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Or install dependencies if setting up fresh
pip install -r backend/requirements.txt
```

---

## 4. Environment Variables

Create your local `.env` file inside `backend/` by copying the template:
```bash
cd backend
cp .env.example .env
```

`backend/app/core/config.py` automatically resolves `backend/.env` regardless of whether the process is launched from `urban-dashboard/` or `backend/`.

| Variable | Description | Example / Default |
|---|---|---|
| `ENVIRONMENT` | Deployment stage | `development` |
| `PORT` | Local server port | `8000` |
| `HOST` | Local server host | `0.0.0.0` |
| `SUPABASE_URL` | Supabase project URL | `https://[PROJECT-REF].supabase.co` |
| `SUPABASE_ANON_KEY` | Public anon key | `eyJhbGciOi...` |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (backend only) | `eyJhbGciOi...` |
| `SUPABASE_STORAGE_BUCKET` | Evidence media bucket | `road-evidence` |
| `DATABASE_URL` | Async PostgreSQL connection string | `postgresql+asyncpg://postgres:[PASS]@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres` |
| `POSTGIS_SCHEMA` | Schema where PostGIS functions reside | `gis` |
| `MAP_MATCH_MAX_DISTANCE_METERS` | Max distance for snapping GPS to road | `25.0` |
| `CONFIDENCE_THRESHOLD` | Threshold to confirm AI observation | `0.50` |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins | `http://localhost:5173,http://localhost:3000` |

> [!IMPORTANT]
> **Supabase Regional IPv4 Session Pooler Requirement (Windows / IPv4 Networks):**  
> Direct Supabase hostnames (`db.<project-ref>.supabase.co`) only provide IPv6 (AAAA) DNS records in AWS regions, causing `[Errno 11001] getaddrinfo failed` crashes on Windows and IPv4 networks.  
> You MUST configure `DATABASE_URL` using Supabase's regional IPv4 Session Pooler host (e.g. `aws-0-ap-northeast-2.pooler.supabase.com:5432` or port `6543`).

> [!CAUTION]
> Never commit `backend/.env` to source control. It is already included in `backend/.gitignore`.

---

## 5. Schema Alignment & Canonical Architecture

The live Supabase database hosts PostgreSQL 17.6 and PostGIS 3.3.7. All 9 canonical entities and views are reconciled and verified with zero data loss:

| Canonical Entity | Type | Role & Primary Key | Description |
|---|---|---|---|
| `buses` | Table | `bus_id VARCHAR(64) PRIMARY KEY` | Fleet vehicle registration, status, and latest telemetry ping coordinates |
| `routes` | Table | `route_id VARCHAR(64) PRIMARY KEY` | Municipal bus routes |
| `trips` | Table | `trip_id VARCHAR(64) PRIMARY KEY` | Scheduled and active bus trips linking buses to routes |
| `road_segments` | Table | `segment_id VARCHAR(64) PRIMARY KEY` | Centerlines (`geom LineString SRID 4326`) and aggregated condition metrics |
| `gps_points` | Table | `point_id BIGSERIAL PRIMARY KEY` | **Authoritative physical source-of-truth table** for raw high-frequency GPS traces |
| `gps_records` | View | Compatibility View over `gps_points` | `CREATE OR REPLACE VIEW gps_records AS SELECT * FROM gps_points;` |
| `observations` | Table | `observation_id VARCHAR(64) PRIMARY KEY` | AI defect/perception detections (`geom Point SRID 4326`, `status VARCHAR(32)`) |
| `incidents` | Table | `incident_id VARCHAR(64) PRIMARY KEY` | Traffic violations & obstructions (`geom Point SRID 4326`, `severity 1-4`) |
| `segment_history`| Table | `history_id BIGSERIAL PRIMARY KEY` | Longitudinal condition history snapshots debounced to 10s intervals |

### Critical GPS Architecture Rule (DO NOT CREATE COMPETING PIPELINES)
- **Physical Table:** `public.gps_points` is the single source-of-truth storing raw GPS coordinates, headings, speeds, and timestamps.
- **Compatibility View:** `public.gps_records` is a non-destructive view mirroring `gps_points`.
- **Developer Warning:** Do **NOT** create a separate `gps_records` table or build a second competing ingestion pipeline. All telemetry routes directly into `gps_points`, and code querying `gps_records` executes with zero overhead.

---

## 6. PostGIS Configuration (`gis` Schema)

PostGIS 3.3.7 functions reside in the **`gis` schema** in Supabase:
- `gis.ST_MakePoint(longitude, latitude)`
- `gis.ST_SetSRID(geometry, 4326)`
- `gis.ST_DWithin(geom1, geom2, distance_meters)`
- `gis.ST_Distance(geom1, geom2)`
- `gis.ST_AsGeoJSON(geometry)`

All coordinates across the platform strictly adhere to the **GeoJSON Standard: `[longitude, latitude]`**.

---

## 7. Database Connection, Pooling & Driver Hardening

- **Driver:** `asyncpg` via SQLAlchemy 2.0 async engine (`postgresql+asyncpg://`).
- **Search Path Enforcement:** Engine is configured with `connect_args={"server_settings": {"search_path": f"public, {settings.POSTGIS_SCHEMA}"}}`, allowing automatic resolution of PostGIS types and functions.
- **Connection Pool:** `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True` to prevent stale connection dropouts across cloud poolers.
- **Elimination of SQLite Fallback:** Silent fallback to in-memory SQLite has been completely removed. `database.py` fails fast at startup if PostgreSQL or `asyncpg` is missing.
- **HTTP 503 Database Error Gateway:** All database connection drops and operational errors are caught by custom exception handlers in `app/core/errors.py` and returned as HTTP 503 `DATABASE_CONNECTION_ERROR` without exposing connection strings or credentials.
- **FastAPI Dependency:** `get_db()` provides a request-scoped `AsyncSession` with automatic rollback on unhandled exceptions.

---

## 8. API Reference

### System Endpoints
| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Service root and navigation links |
| `GET` | `/health` | Application health, timestamp, and environment |
| `GET` | `/health/database` | PostgreSQL & PostGIS connectivity and entity verification |

### Road Segments
- **`GET /api/v1/segments/geojson`**
  - **Query Params:** `format` (`'geojson'` default, `'flat'` for direct array)
  - **Response:** GeoJSON `FeatureCollection` containing LineString features with properties:
    `segment_id`, `name`, `condition_score`, `confidence`, `pothole_count`, `waterlogging_count`, `observation_count`, `last_updated`.
- **`GET /api/v1/segments/{segment_id}`**
  - **Response:** Current condition and properties of a single road segment.
- **`GET /api/v1/segments/{segment_id}/history`**
  - **Response:** Chronological condition score timeline.

### Events & Observations
- **`GET /api/v1/events`**
  - **Query Params:** `event_type`, `road_segment_id`, `min_severity` (1–4), `limit` (default 50), `offset` (default 0).
  - **Response:** Array of validated detection events with descriptive text severity.
- **`POST /api/v1/observations`**
  - **Status Code:** `201 Created`
  - **Request Body:** Structured AI detection matching `AI_CONTRACT.md` and accepting optional diagnostic metrics: `risk_score`, `risk_level`, `breadth_cm`, `depth_cm`, `dimensions`, `risk_assessment`, and `metadata` (JSONB).
  - **Processing:** Confidence filtering, map-matching, road score recalculation, and live broadcast.

### Incidents
- **`GET /api/v1/incidents`**
  - **Query Params:** `status`, `limit`, `offset`.
  - **Response:** Traffic violations, obstructions, and vehicle tracking events.
- **`POST /api/v1/incidents`**
  - **Status Code:** `201 Created`
  - **Request Body:** New incident with optional vehicle tracking and OCR fields (`plate_text`, `plate_confidence`).

### Fleet Buses & Telemetry
- **`GET /api/v1/buses`**
  - **Response:** List of active buses with their latest coordinates and status.
- **`POST /api/v1/telemetry`**
  - **Status Code:** `201 Created`
  - **Request Body:** `{"bus_id": "TEST-BUS-001", "latitude": 30.7333, "longitude": 76.7794, "speed_kmh": 32.5, "heading_deg": 142.0}`
  - **Processing:** Inserts GPS trace into `gps_points`, updates `buses`, broadcasts `BUS_TELEMETRY`.

### Analytics & Infrastructure KPIs
- **`GET /api/v1/analytics/summary`**
  - **Response:** Aggregate infrastructure condition, active fleet count, total defects/incidents, and condition tier distribution (`healthy`, `moderate`, `poor`, `critical`).

### Edge Video Ingestion Pipeline
- **`GET /api/v1/ingest/video/status`**
  - **Response:** Video processing status, progress percentage, current/total frames, and completion summary.
- **`POST /api/v1/ingest/video/process`**
  - **Request:** Multipart form upload or synthetic sample trigger. Dispatches edge video frames through preserved AI detectors and normalizes outputs via `BackendIngestAdapter`.

---

## 9. WebSocket Protocol (`/ws/live`)

Clients connect via `ws://localhost:8000/ws/live` to receive real-time streams and send heartbeats.

### Heartbeat (Ping / Pong)
- Client sends: `"ping"`
- Server responds: `{"type": "PONG"}`

### Broadcast Frames:
1. `BUS_TELEMETRY`: Dispatched upon vehicle GPS updates via `/api/v1/telemetry`.
2. `NEW_EVENT`: Dispatched upon confirmed defect observation ingestion (`confidence >= 0.50`).
3. `NEW_INCIDENT`: Dispatched immediately upon traffic violation/incident registration.
4. `SEGMENT_UPDATE`: Dispatched when a road segment's condition score or counters are updated.

---

## 10. AI Ingestion Pipeline & Adapter Boundary

The `/api/v1/observations` endpoint enforces strict validation rules:
1. **Coordinate Boundaries:** Latitude $\in [-90, 90]$, Longitude $\in [-180, 180]$.
2. **OCR Validation Rule:** If `plate_text` is supplied, `plate_confidence` is **strictly required**. Omitting `plate_confidence` returns `HTTP 422 Unprocessable Entity`.
3. **Confidence Quarantining (< 0.50):**
   - Observations with `confidence < 0.50` are automatically persisted with `status = 'quarantined'`.
   - Returns `HTTP 201 Created` with `{"quarantined": true, "status": "quarantined"}`.
   - Quarantined observations do **not** trigger road score penalties, do **not** insert history snapshots, and are **not** broadcast to live dashboard clients.
4. **Confirmed Observations (>= 0.50):**
   - Persisted with `status = 'confirmed'`.
   - Snapped to nearest road segment via PostGIS `map_matching`.
   - Triggers `recalculate_segment_metrics`, updates `road_segments`, inserts debounced `segment_history`, and broadcasts `NEW_EVENT`.
5. **AI Diagnostic Metrics Preservation:**
   - Any AI diagnostics (`risk_score`, `risk_level`, `breadth_cm`, `depth_cm`, `dimensions`, `risk_assessment`) passed in the payload are preserved directly in `Observation.metadata_json` (PostgreSQL `observations.metadata` JSONB column).
6. **Media Hygiene:** Base64 binaries are prohibited in JSON payloads. Images must be stored in object storage and passed as `evidence_uri`.

---

## 11. Map Matching Service

When an edge AI observation arrives without a pre-computed `road_segment_id`:
1. The service queries PostGIS in the `gis` schema using geography casting for metric distance:
   ```sql
   SELECT segment_id, name,
          gis.ST_Distance(geom::gis.geography, gis.ST_SetSRID(gis.ST_MakePoint(:lng, :lat), 4326)::gis.geography) AS distance_meters
   FROM road_segments
   WHERE gis.ST_DWithin(geom::gis.geography, gis.ST_SetSRID(gis.ST_MakePoint(:lng, :lat), 4326)::gis.geography, :max_dist)
   ORDER BY distance_meters ASC LIMIT 1;
   ```
2. Snaps to the segment if within `MAP_MATCH_MAX_DISTANCE_METERS` (default `25.0` meters).

---

## 12. Road Health Scoring Formula & Clean-Pass Recovery

Road segment health scores ($0.00 - 100.00$) are calculated deterministically:

$$\text{Base Score} = 100.0$$

$$\text{Severity Penalty Weights} = \{1: 2.0, \; 2: 5.0, \; 3: 10.0, \; 4: 20.0\}$$

$$\text{Frequency Multiplier} = 1.0 + \Big(0.2 \times \min\big(\max(0, \text{Count}_{\text{same\_type}} - 1), 4\big)\Big)$$

$$\text{Defect Penalty} = \sum_{\text{obs} \in \text{Confirmed Defects}} \Big(\text{Weight}[\text{severity}] \times \text{Frequency Multiplier} \times \text{Confidence}\Big)$$

$$\text{Clean-Pass Recovery Bonus} = \text{Clean Pass Count} \times 5.0$$

$$\text{Health Score} = \max\Big(0.0, \; \min\big(100.0, \; \text{round}(100.0 - \text{Defect Penalty} + \text{Clean-Pass Recovery Bonus}, 2)\big)\Big)$$

---

## 13. Aggregation & Longitudinal History Debouncing

Upon receiving a confirmed observation on a segment:
1. All confirmed observations on the segment are aggregated.
2. Defect counters are recomputed (`pothole_count`, `waterlogging_count`, `observation_count`).
3. The `road_segments` record is updated with the new score and counts.
4. **History Snapshot Debouncing:** Snapshots within a 10-second window update the existing record in place rather than inserting redundant microsecond duplicate rows.
5. **Real-Time Broadcast:** Immediately broadcasts `LiveSegmentUpdateFrame` (`SEGMENT_UPDATE`) over `/ws/live`.

---

## 14. Supabase Storage Integration

- **Bucket:** `road-evidence` (configured in Supabase Storage).
- **Upload:** `services/evidence.py` handles uploading media bytes.
- **Signed URLs:** Time-limited signed URLs (default TTL 3600s) are generated for secure private bucket access upon API serialization.

---

## 15. Severity Architecture

| Numeric Level | Descriptive Text | Penalty Weight | Description |
|---|---|---|---|
| `1` | `"low"` | 2.0 | Minor hairline cracks, shallow wear |
| `2` | `"moderate"` | 5.0 | Medium potholes, localized waterlogging |
| `3` | `"high"` | 10.0 | Deep potholes, major lane obstruction |
| `4` | `"critical"` | 20.0 | Severe road collapse, deep submerged road |

---

## 16. Error Handling Contract

All error responses strictly adhere to the contract defined in `API_CONTRACT.md` Section 4:
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Road segment with ID 'seg_999' was not found.",
    "timestamp": "2026-09-08T00:30:00+05:30"
  }
}
```

---

## 17. Running Locally & Launchers

### Preferred Method (Zero-Friction Dev Launch):
From the repository root:
```powershell
.\start-dev.ps1
```

### Dedicated Backend Launchers:
From repository root:
```powershell
.\start-backend.ps1
```
*(Or on cmd.exe: `.\start-backend.bat`)*

Or run manually with Python:
```bash
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Interactive Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Database Health Check:** [http://localhost:8000/health/database](http://localhost:8000/health/database)

---

## 18. Diagnostic & Simulation Scripts

### 1. Test Supabase & PostGIS Connectivity
```bash
python -m backend.scripts.test_connection
```
Validates PostgreSQL connection, checks PostGIS in the `gis` schema, queries all 9 canonical entities/views, and tests storage bucket accessibility.

### 2. Run End-to-End Simulation (6-Stage Pipeline)
```bash
python -m backend.scripts.test_ingestion
```

### 3. Seed Canonical Chandigarh Demo Data
```bash
python -m backend.scripts.seed_chandigarh_demo
```

### 4. Run Live Fleet Bus Simulator
```bash
python -m backend.scripts.simulate_chandigarh_buses
```

---

## 19. Testing Suite

Run the full automated test suite:
```bash
pytest -v
```

**Test Results: 47/47 Passed (100% Pass Rate)**

The test suite covers:
- **AI & Adapter Integration (`tests/test_ai_integration.py`):** Schema normalization, OCR plate validation, AI diagnostic metadata preservation, video status router, and live WebSocket broadcasts.
- **Real Database & PostGIS Integration (`tests/test_integration_real.py`):** Live PostgreSQL 17.6 connection via pooler, PostGIS distance calculations in `gis` schema, canonical entities/views existence, `gps_records` view parity, real spatial map-matching against Chandigarh coordinates, confidence weighting & clean-pass recovery.
- **Scoring & Recovery (`tests/test_scoring.py`):** Clean road baseline, single/repeated defect penalties, condition thresholds, and clean-pass recovery credits.
- **API Routes & Schemas (`tests/test_api_routes.py`):** Canonical buses serialization (`bus_id` + `vehicle_number`), GeoJSON and flat segment formats, SQL-level severity filtering, and OCR rule enforcement.
- **Telemetry & Validation (`tests/test_validation.py`, `tests/test_coordinates.py`):** Bounding boxes, WKT conversions, GeoJSON parsers, and edge validation rules.
- **WebSocket Manager (`tests/test_websocket.py`):** Client connection, frame broadcasting, heartbeat ping/pong, and dead connection cleanup.
- **Configuration & Drivers (`tests/test_config.py`):** CORS origins parsing, `asyncpg` scheme transformation, and environment defaults.

---

## 20. Frontend Integration

To connect the React/Vite dashboard to this FastAPI backend:
1. In the repository root, configure your frontend `.env`:
   ```env
   VITE_API_BASE_URL=http://localhost:8000
   VITE_USE_MOCK=false
   ```
2. Start the development environment:
   ```powershell
   .\start-dev.ps1
   ```
3. Open [http://localhost:5173](http://localhost:5173). The dashboard will fetch live road segments, events, incidents, and buses from the FastAPI backend and stream real-time telemetry over WebSocket!
