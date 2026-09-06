# SIH 26124: FastAPI Backend for Urban Intelligence Platform

> **AI-Powered Mobile Urban Intelligence Platform Using Public Transport Fleet**  
> Complete FastAPI backend connecting to the **existing Supabase PostgreSQL + PostGIS database** and providing REST and WebSocket APIs for the React GIS dashboard and edge AI perception ingestion.

---

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Installation](#3-installation)
4. [Environment Variables](#4-environment-variables)
5. [Schema Alignment & Migration](#5-schema-alignment--migration)
6. [PostGIS Configuration (`gis` Schema)](#6-postgis-configuration-gis-schema)
7. [Database Connection & Pooling](#7-database-connection--pooling)
8. [API Reference](#8-api-reference)
9. [WebSocket Protocol (`/ws/live`)](#9-websocket-protocol-wslive)
10. [AI Ingestion Pipeline & Validation](#10-ai-ingestion-pipeline--validation)
11. [Map Matching Service](#11-map-matching-service)
12. [Road Health Scoring Formula](#12-road-health-scoring-formula)
13. [Aggregation & Longitudinal History](#13-aggregation--longitudinal-history)
14. [Supabase Storage Integration](#14-supabase-storage-integration)
15. [Severity Architecture (Internal 1–4 vs Descriptive UI Text)](#15-severity-architecture)
16. [Error Handling Contract](#16-error-handling-contract)
17. [Running Locally](#17-running-locally)
18. [Diagnostic & Simulation Scripts](#18-diagnostic--simulation-scripts)
19. [Testing Suite](#19-testing-suite)
20. [Frontend Integration](#20-frontend-integration)

---

## 1. Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                           Edge AI Sensing Fleet                         │
│                    (Buses with Cameras & GPS Trackers)                  │
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

## 3. Installation

From the project root:
```bash
cd backend
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# On macOS/Linux:
source .venv/bin/activate

# Install pinned dependencies
pip install -r requirements.txt
```

---

## 4. Environment Variables

Create your local `.env` file by copying the template:
```bash
cp .env.example .env
```

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

### Safe Migration & Legacy NOT NULL Constraints
1. **Schema Reconciliation:** Executed [`scripts/migrate_to_documented_schema.sql`](scripts/migrate_to_documented_schema.sql) in the Supabase SQL Editor. It establishes canonical primary keys (`bus_id`, `segment_id`, `observation_id`, `incident_id`), re-establishes foreign keys, builds GiST spatial indexes, and creates `routes`, `trips`, and `gps_records`.
2. **Legacy NOT NULL Removal:** Standalone utility [`scripts/drop_legacy_notnull.py`](scripts/drop_legacy_notnull.py) was executed to drop superseded NOT NULL constraints on legacy columns (`legacy_bus_id`, `latitude`, `longitude`, `location`, `legacy_severity`, `detected_at`, `observation_type`, `geometry`, `road_segment_id`) while preserving historical values, ensuring seamless canonical inserts.

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
| `GET` | `/health` | Application health and timestamp |
| `GET` | `/health/database` | PostgreSQL & PostGIS connectivity verification |

### Road Segments
- **`GET /api/v1/segments/geojson`**
  - **Query Params:** `format` (`'geojson'` default, `'flat'` for direct array)
  - **Response:** GeoJSON `FeatureCollection` containing LineString features with properties:
    `segment_id`, `name`, `condition_score`, `confidence`, `pothole_count`, `waterlogging_count`, `observation_count`, `last_updated`.
- **`GET /api/v1/segments/{segment_id}`**
  - **Response:** Current condition and properties of a single road segment.
- **`GET /api/v1/segments/{segment_id}/history`**
  - **Response:** Chronological condition score timeline: `[{"timestamp": "...", "date": "...", "condition_score": 85.5, "score": 85.5, "confidence": 0.92, "pothole_count": 1}, ...]`.

### Events & Observations
- **`GET /api/v1/events`**
  - **Query Params:** `event_type`, `road_segment_id`, `min_severity` (1–4), `limit` (default 50), `offset` (default 0).
  - **Response:** Array of validated detection events with descriptive text severity.
- **`POST /api/v1/observations`**
  - **Status Code:** `201 Created`
  - **Request Body:** Structured AI detection matching `AI_CONTRACT.md`.
  - **Processing:** Confidence filtering, map-matching, road score recalculation, and live broadcast.

### Incidents
- **`GET /api/v1/incidents`**
  - **Query Params:** `status`, `limit`, `offset`.
  - **Response:** Traffic violations, obstructions, and vehicle tracking events.
- **`POST /api/v1/incidents`**
  - **Status Code:** `201 Created`
  - **Request Body:** New incident with optional vehicle tracking and OCR fields.

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

---

## 9. WebSocket Protocol (`/ws/live`)

Clients connect via `ws://localhost:8000/ws/live` to receive real-time streams and send heartbeats.

### Heartbeat (Ping / Pong)
- Client sends: `"ping"`
- Server responds: `{"type": "PONG"}`

### Frame 1: `BUS_TELEMETRY`
Emitted when new vehicle GPS telemetry arrives via `/api/v1/telemetry`:
```json
{
  "type": "BUS_TELEMETRY",
  "payload": {
    "bus_id": "TEST-BUS-001",
    "latitude": 30.7348,
    "longitude": 76.7805,
    "heading_deg": 145.0,
    "timestamp": "2026-09-04T12:00:00+05:30",
    "status": "active"
  }
}
```

### Frame 2: `NEW_EVENT`
Emitted when a confirmed road defect observation is ingested via `/api/v1/observations`:
```json
{
  "type": "NEW_EVENT",
  "payload": {
    "event_id": "evt_20260904_001",
    "bus_id": "TEST-BUS-001",
    "timestamp": "2026-09-04T12:00:05+05:30",
    "latitude": 30.7360,
    "longitude": 76.7830,
    "road_segment_id": "seg_chandigarh_001",
    "event_type": "road_defect",
    "class_name": "pothole_deep",
    "confidence": 0.92,
    "severity": 3,
    "severity_label": "high",
    "frame_id": 4120,
    "evidence_uri": "https://storage.urban-intel.city/frames/evt_001.jpg"
  }
}
```

### Frame 3: `NEW_INCIDENT`
Emitted immediately when a new traffic violation/incident is created via `/api/v1/incidents`:
```json
{
  "type": "NEW_INCIDENT",
  "payload": {
    "incident_id": "inc_20260904_001",
    "incident_type": "illegal_parking",
    "severity": 2,
    "severity_label": "moderate",
    "incident_score": 50.0,
    "vehicle_track_id": "trk_901",
    "plate_text": "CH01AB1234",
    "plate_confidence": 0.95,
    "latitude": 30.7350,
    "longitude": 76.7820,
    "timestamp": "2026-09-04T12:00:10+05:30",
    "road_segment_id": "seg_chandigarh_001",
    "observation_id": null,
    "evidence_uri": "https://[PROJECT-REF].supabase.co/storage/v1/object/sign/road-evidence/uploads/inc_001.jpg?token=...",
    "description": "Vehicle blocking designated bus corridor",
    "status": "open"
  }
}
```

### Frame 4: `SEGMENT_UPDATE`
Emitted when a road segment's condition metrics are recalculated after an observation:
```json
{
  "type": "SEGMENT_UPDATE",
  "payload": {
    "segment_id": "seg_chandigarh_001",
    "condition_score": 85.5,
    "pothole_count": 1,
    "waterlogging_count": 0,
    "observation_count": 15,
    "last_updated": "2026-09-04T12:00:15+05:30"
  }
}
```

---

## 10. AI Ingestion Pipeline & Validation

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
5. **Media Hygiene:** Base64 binaries are prohibited in JSON payloads. Images must be stored in object storage and passed as `evidence_uri`.

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

### Condition Categories:
- **Good:** $\text{Score} \ge 80.0$
- **Fair:** $60.0 \le \text{Score} < 80.0$
- **Poor:** $40.0 \le \text{Score} < 60.0$
- **Critical:** $\text{Score} < 40.0$

---

## 13. Aggregation & Longitudinal History Debouncing

Upon receiving a confirmed observation on a segment:
1. All confirmed observations on the segment are aggregated.
2. Defect counters are recomputed (`pothole_count`, `waterlogging_count`, `observation_count`).
3. The `road_segments` record is updated with the new score and counts.
4. **History Snapshot Debouncing (BUG-006 Resolution):** `aggregation.py` checks the latest `SegmentHistory` record. Snapshots within a 10-second window update the existing record in place rather than inserting redundant microsecond duplicate rows.
5. **Real-Time Broadcast (BUG-017 Resolution):** Immediately broadcasts `LiveSegmentUpdateFrame` (`SEGMENT_UPDATE`) over `/ws/live`.

---

## 14. Supabase Storage Integration

- **Bucket:** `road-evidence` (configured in Supabase Storage).
- **Upload:** `services/evidence.py` handles uploading media bytes.
- **Signed URLs:** Time-limited signed URLs (default TTL 3600s) are generated for secure private bucket access.

---

## 15. Severity Architecture

| Numeric Level | Descriptive Text | Penalty Weight | Description |
|---|---|---|---|
| `1` | `"low"` | 2.0 | Minor hairline cracks, shallow wear |
| `2` | `"moderate"` | 5.0 | Medium potholes, localized waterlogging |
| `3` | `"high"` | 10.0 | Deep potholes, major lane obstruction |
| `4` | `"critical"` | 20.0 | Severe road collapse, deep submerged road |

- **Internal Storage & Processing:** Numeric 1–4 matching `AI_CONTRACT.md`.
- **API & Dashboard Output:** Descriptive string (`"low"`, `"moderate"`, `"high"`, `"critical"`) matching user requirements.

---

## 16. Error Handling Contract

All error responses strictly adhere to the contract defined in `API_CONTRACT.md` Section 4:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Road segment with ID 'seg_999' was not found.",
    "timestamp": "2026-09-04T12:00:00+05:30"
  }
}
```

Standard Error Codes:
- `RESOURCE_NOT_FOUND` (404)
- `VALIDATION_ERROR` (422)
- `BAD_REQUEST` (400)
- `DATABASE_CONNECTION_ERROR` (503)
- `INTERNAL_SERVER_ERROR` (500)

---

## 17. Running Locally

Start the development server:
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Interactive Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Database Health Check:** [http://localhost:8000/health/database](http://localhost:8000/health/database)

---

## 18. Diagnostic & Simulation Scripts

### 1. Test Supabase & PostGIS Connectivity
```bash
cd backend
python scripts/test_connection.py
```
Validates PostgreSQL connection, checks PostGIS in the `gis` schema, queries all 9 canonical entities/views (`buses`, `gps_points`, `road_segments`, `observations`, `incidents`, `segment_history`, `routes`, `trips`, `gps_records`), and tests storage bucket accessibility.

### 2. Run End-to-End Simulation (6-Stage Pipeline)
```bash
cd backend
python scripts/test_ingestion.py
```
Simulates the entire pipeline across 6 validation stages:
- **Step 0:** Server Health Check (`/health`, `/health/database`)
- **Step 1:** GPS Telemetry Ingestion (`/api/v1/telemetry`)
- **Step 2:** OCR Validation Rule Enforcement (rejection with HTTP 422 if `plate_text` lacks `plate_confidence`)
- **Step 3:** Low-Confidence Quarantine (confidence < 0.50 marked quarantined, HTTP 201)
- **Step 4:** Confirmed Observation Ingestion (confidence >= 0.50, map-matched & scored)
- **Step 5:** GeoJSON Network Export (`/api/v1/segments/geojson`)
- **Step 6:** WebSocket Live Connection (`/ws/live` ping/pong heartbeat)

### 3. Seed Canonical Chandigarh Demo Data
```bash
cd backend
python scripts/seed_chandigarh_demo.py
```
Seeds PostGIS `road_segments.geom` with OSM-derived canonical geometries from `data/chandigarh_roads_canonical.geojson`, registers 11 fleet buses, populates 20 confirmed defect observations, and seeds 7 traffic incidents.

### 4. Run Live Fleet Bus Simulator
```bash
cd backend
python scripts/simulate_chandigarh_buses.py
```
Streams continuous live GPS telemetry points to `POST /api/v1/telemetry` along canonical road centerlines, triggering live `BUS_TELEMETRY` broadcasts to connected WebSocket clients.

### 5. Drop Legacy NOT NULL Constraints
```bash
cd backend
python scripts/drop_legacy_notnull.py
```
Idempotently drops superseded NOT NULL constraints on legacy columns (`legacy_bus_id`, `latitude`, `longitude`, `location`, `legacy_severity`, `detected_at`, `observation_type`, `geometry`, `road_segment_id`) while preserving historical values.

---

## 19. Testing Suite

Run the full automated test suite:
```bash
cd backend
pytest -v
```

**Test Results: 40/40 Passed (100% Pass Rate)**

The test suite covers:
- **Real Database & PostGIS Integration (`tests/test_integration_real.py`):** Live PostgreSQL 17.6 connection via pooler, PostGIS distance calculations in `gis` schema, canonical entities/views existence, `gps_records` view parity, real spatial map-matching against Chandigarh coordinates, confidence weighting & clean-pass recovery.
- **Scoring & Recovery (`tests/test_scoring.py`):** Clean road baseline, single/repeated defect penalties, condition thresholds (`good`, `fair`, `poor`, `critical`), confidence factor scaling (`weight_by_confidence=True`), and clean-pass recovery credits (+5.0 points per clean pass).
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
2. Start the frontend:
   ```bash
   npm run dev
   ```
3. Open [http://localhost:5173](http://localhost:5173). The dashboard will fetch live road segments, events, incidents, and buses from the FastAPI backend and stream real-time telemetry over WebSocket!
