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
│  │     Existing Supabase PostgreSQL Database (Public Schema)         │  │
│  │   (buses, gps_points, road_segments, observations, incidents,    │  │
│  │                          segment_history)                         │  │
│  └──────────────────────────────────┬────────────────────────────────┘  │
│                                     │ WebSocket Broadcast               │
└─────────────────────────────────────┼───────────────────────────────────┘
                                      │ /ws/live (BUS_TELEMETRY, NEW_EVENT)
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
| `SUPABASE_URL` | Supabase project URL | `https://xyzcompany.supabase.co` |
| `SUPABASE_ANON_KEY` | Public anon key | `eyJhbGciOi...` |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (backend only) | `eyJhbGciOi...` |
| `SUPABASE_STORAGE_BUCKET` | Evidence media bucket | `road-evidence` |
| `DATABASE_URL` | Async PostgreSQL connection string | `postgresql+asyncpg://postgres:[PASS]@[HOST]:5432/postgres` |
| `POSTGIS_SCHEMA` | Schema where PostGIS functions reside | `gis` |
| `MAP_MATCH_MAX_DISTANCE_METERS` | Max distance for snapping GPS to road | `25.0` |
| `CONFIDENCE_THRESHOLD` | Threshold to confirm AI observation | `0.50` |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins | `http://localhost:5173,http://localhost:3000` |

> [!CAUTION]
> Never commit `backend/.env` to source control. It is already included in `backend/.gitignore`.

---

## 5. Schema Alignment & Migration

> [!IMPORTANT]
> **DO NOT DROP TABLES IN SUPABASE!**  
> To reconcile the existing Supabase tables (`buses`, `gps_points`, `road_segments`, `observations`, `incidents`, `segment_history`) with canonical contracts without data loss, use the production reconciliation script.

### Discrepancy Resolution & Safe Migration
The initial database schema used legacy column names and UUID primary keys. The backend models and API routes are built against canonical names (`segment_id`, `geom`, `condition_score`, `observed_at`, `event_type`).

To reconcile the schema safely within a single transaction:
1. Open the **SQL Editor** in your Supabase Dashboard.
2. Copy and execute [`scripts/migrate_to_documented_schema.sql`](scripts/migrate_to_documented_schema.sql).

This script idempotently and safely:
- Validates preflight assumptions (verifies all 6 tables exist and PostGIS is installed).
- Preserves all legacy UUIDs and columns (`road_name`, `health_score`, `location`) as auxiliary columns without dropping data.
- Adds canonical columns (`segment_id`, `geom`, `condition_score`, `event_type`, `observed_at`, `evidence_uri`).
- Converts severity values using explicit contract mapping rules.
- Re-establishes all 6 foreign key constraints with verified `ON DELETE` rules.
- Creates GiST spatial indexes on all spatial columns using the `gis` schema.
- Resets BIGSERIAL sequences safely to `MAX(id) + 1`.

See [`../docs/BUGS_AND_DISCREPANCIES.md`](../docs/BUGS_AND_DISCREPANCIES.md) for full defect analysis and resolution details.

---

## 6. PostGIS Configuration (`gis` Schema)

PostGIS functions are installed under the **`gis` schema** in Supabase:
- `gis.ST_MakePoint(longitude, latitude)`
- `gis.ST_SetSRID(geometry, 4326)`
- `gis.ST_DWithin(geom1, geom2, distance_meters)`
- `gis.ST_Distance(geom1, geom2)`
- `gis.ST_AsGeoJSON(geometry)`

All API coordinates adhere strictly to the **GeoJSON Standard: `[longitude, latitude]`**.

---

## 7. Database Connection & Pooling

- **Driver:** `asyncpg` via SQLAlchemy 2.0 async engine (`postgresql+asyncpg://`).
- **Connection Pool:** `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True` to prevent stale connection timeouts across cloud poolers.
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

---

## 9. WebSocket Protocol (`/ws/live`)

Clients connect via `ws://localhost:8000/ws/live` to receive real-time updates.

### Frame 1: `BUS_TELEMETRY`
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
```json
{
  "type": "NEW_EVENT",
  "payload": {
    "event_id": "evt_20260904_001",
    "bus_id": "TEST-BUS-001",
    "timestamp": "2026-09-04T12:00:05+05:30",
    "latitude": 30.7360,
    "longitude": 76.7830,
    "road_segment_id": "de79e250-5dea-4ecd-85bb-25f972d9d91c",
    "event_type": "road_defect",
    "class_name": "pothole_deep",
    "confidence": 0.92,
    "severity": "high",
    "severity_level": 3,
    "frame_id": 4120,
    "evidence_uri": "https://storage.urban-intel.city/frames/evt_001.jpg"
  }
}
```

---

## 10. AI Ingestion Pipeline & Validation

The `/api/v1/observations` endpoint enforces strict validation rules:
1. **Coordinate Boundaries:** Latitude $\in [-90, 90]$, Longitude $\in [-180, 180]$.
2. **OCR Rule:** If `plate_text` is supplied, `plate_confidence` is **strictly required**. Missing confidence returns `HTTP 422 Unprocessable Entity`.
3. **Confidence Quarantining:**
   - Observations with `confidence < 0.50` are marked as `'quarantined'`.
   - Quarantined observations are persisted for auditor review, but do **not** trigger road score penalties and are **not** broadcast to live dashboard clients.
4. **Media Hygiene:** Base64 binaries are prohibited in JSON payloads. Images must be stored in object storage and passed as `evidence_uri`.

---

## 11. Map Matching Service

When an edge AI observation arrives without a pre-computed `road_segment_id`:
1. The service queries PostGIS in the `gis` schema using geography casting for metric distance:
   ```sql
   SELECT id, road_name,
          gis.ST_Distance(geometry::geography, gis.ST_SetSRID(gis.ST_MakePoint(:lng, :lat), 4326)::geography) AS distance_meters
   FROM road_segments
   WHERE gis.ST_DWithin(geometry::geography, gis.ST_SetSRID(gis.ST_MakePoint(:lng, :lat), 4326)::geography, :max_dist)
   ORDER BY distance_meters ASC LIMIT 1;
   ```
2. Snaps to the segment if within `MAP_MATCH_MAX_DISTANCE_METERS` (default `25.0` meters).

---

## 12. Road Health Scoring Formula

Road segment health scores ($0.00 - 100.00$) are calculated deterministically:

$$\text{Base Score} = 100.0$$

$$\text{Severity Penalty Weights} = \{1: 2.0, \; 2: 5.0, \; 3: 10.0, \; 4: 20.0\}$$

$$\text{Frequency Multiplier} = 1.0 + \Big(0.2 \times \min\big(\max(0, \text{Count}_{\text{same\_type}} - 1), 4\big)\Big)$$

$$\text{Total Penalty} = \sum_{\text{obs} \in \text{Confirmed}} \big(\text{Weight}[\text{severity}] \times \text{Frequency Multiplier}\big)$$

$$\text{Health Score} = \max\big(0.0, \; \min(100.0, \; 100.0 - \text{Total Penalty})\big)$$

### Condition Categories:
- **Good:** $\text{Score} \ge 80.0$
- **Fair:** $60.0 \le \text{Score} < 80.0$
- **Poor:** $40.0 \le \text{Score} < 60.0$
- **Critical:** $\text{Score} < 40.0$

---

## 13. Aggregation & Longitudinal History

Upon receiving a confirmed observation on a segment:
1. All confirmed observations on the segment are aggregated.
2. Defect counters are recomputed:
   - `pothole_count`: detections matching pothole defect classes.
   - `crack_count`: major/minor alligator cracks.
   - `rough_surface_count`: surface wear and rutting.
   - `waterlogging_count`: submerged lane and water patch events.
3. The `road_segments` record is updated with the new score and counts.
4. An immutable point-in-time snapshot is appended to `segment_history`.

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
Validates credentials, checks PostGIS in the `gis` schema, queries tables, and tests the storage bucket.

### 2. Run End-to-End Simulation
```bash
cd backend
python scripts/test_ingestion.py
```
Simulates the entire pipeline: GPS telemetry ingestion, OCR validation rejection, low-confidence quarantine, confirmed observation processing, and WebSocket broadcasting.

---

## 19. Testing Suite

Run the full automated test suite:
```bash
cd backend
pytest -v
```

The test suite covers:
- Configuration parsing & asyncpg URL transformation.
- Bidirectional severity conversions and penalty weights.
- Coordinate boundaries and WKT/GeoJSON transformations.
- Road scoring formula and edge cases.
- Pydantic schema validation and OCR rules.
- System health endpoints.
- WebSocket connection management and dead-client cleanup.

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
