# Comprehensive Bug, Defect & Discrepancy Register

> **Status:** Active Reference & Remediation Backlog  
> **Date:** September 2026  
> **Scope:** Cross-Subsystem Audit (Frontend Dashboard, FastAPI Backend, PostgreSQL/PostGIS Database, Edge AI Ingestion, WebSocket Protocol)

---

## 1. Executive Summary

Following the introduction of the **FastAPI Backend v1** (commit `873553f`), a comprehensive end-to-end audit was conducted across the codebase, database scripts, API contracts, AI perception contracts, and frontend components.

A total of **14 issues** have been identified and cataloged below:
- **3 Critical Severity** (direct runtime crashes or total feature failures upon live connection)
- **4 High Severity** (data loss, silent drop of real-time telemetry, or database query failures)
- **4 Medium Severity** (contract violations, race conditions, or hardcoded environment paths)
- **3 Low / Hygiene Severity** (documentation broken links, missing reconnection backoff, test mock sync)

---

## 2. Bug & Discrepancy Summary Table

| ID | Title | Subsystems | Severity | Impact | Status |
|---|---|---|---|---|---|
| **BUG-001** | `GET /api/v1/segments/geojson` Response Shape Mismatch | Frontend / Backend | **CRITICAL** | Frontend runtime crash (`segments.map is not a function`) when live backend is enabled | Open |
| **BUG-002** | Incident Metric Discrepancy: `incident_score` vs `severity` | Frontend / Backend / Contracts | **CRITICAL** | Data loss / undefined display in Incident Inspector | Open |
| **BUG-003** | Database Schema Dual-State / Column Naming Discrepancy | Backend / Database | **CRITICAL** | All backend SQL queries fail if `migrate_to_documented_schema.sql` has not been executed | Open |
| **BUG-004** | Frontend WebSocket Client Disconnected from UI State | Frontend / WebSocket | **HIGH** | Real-time bus telemetry and new event markers are completely ignored by the UI | Open |
| **BUG-005** | Map-Matching PostGIS Fallback Query Schema Qualification Flaw | Backend Service | **HIGH** | Fallback map-matching query fails if PostGIS functions are strictly isolated in `gis` schema | Open |
| **BUG-006** | Segment History Multi-Insert Duplication on Bulk Ingestion | Backend Ingestion / DB | **HIGH** | `segment_history` is flooded with duplicate snapshots per defect instead of per pass | Open |
| **BUG-007** | Evidence Signed URL Expiration Causes Broken Media in UI | Backend Storage / Frontend | **HIGH** | Defect and incident evidence images stop loading after 1 hour (3600s) | Open |
| **BUG-008** | Segment ID Formatting Inconsistency (Hyphen vs Underscore) | Frontend Mock / Backend DB | **MEDIUM** | Filter and inspector lookups fail when mixing mock and live identifiers | Open |
| **BUG-009** | SQLite In-Memory Database Fallback Incompatible with PostGIS | Backend Database | **MEDIUM** | In-memory fallback crashes immediately on spatial queries (`ST_AsGeoJSON`, `ST_DWithin`) | Open |
| **BUG-010** | Missing WebSocket Auto-Reconnection & Backoff in Frontend | Frontend WebSocket | **MEDIUM** | Dropped WebSocket connections are permanently abandoned until hard refresh | Open |
| **BUG-011** | Contradictory Database Migration Instructions in Documentation | Backend README / Docs | **MEDIUM** | Developers running `migrate_schema.sql` instead of `migrate_to_documented_schema.sql` break backend | Open |
| **BUG-012** | Event Query Parameter Type Coercion (`min_severity`) | Backend API / Frontend | **MEDIUM** | Potential 422 Unprocessable Entity if non-integer severity or text severity is queried | Open |
| **BUG-013** | Hardcoded Absolute Machine File Links in Project Documentation | Documentation | **LOW** | Broken documentation links across external developer machines | Open |
| **BUG-014** | Missing Automated Integration Tests for Live API Hydration | Testing Suite | **LOW** | No end-to-end CI test verifying frontend parsing of live backend payloads | Open |

---

## 3. Detailed Defect Analysis & Remediation Plan

---

### BUG-001: `GET /api/v1/segments/geojson` Response Shape Mismatch

- **Severity:** `CRITICAL`
- **Affected Files:**
  - `src/services/api.ts` (Line 23–27)
  - `src/types/roadSegments.ts` (Line 1–12)
  - `backend/app/api/v1/segments.py` (Line 25–134)
  - `docs/API_CONTRACT.md` (Section 2.1)
- **Problem Description:**  
  `docs/API_CONTRACT.md` defines `GET /api/v1/segments/geojson` as returning a standard GeoJSON `FeatureCollection` object:
  ```json
  {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "id": "seg_chandigarh_001",
        "geometry": { "type": "LineString", "coordinates": [...] },
        "properties": { "segment_id": "seg_chandigarh_001", ... }
      }
    ]
  }
  ```
  The backend implementation supports this default, and also provides an optional `?format=flat` query param which returns a flat array `RoadSegmentFlat[]`.
  However, the frontend `src/services/api.ts` defines:
  ```ts
  export async function fetchSegments(): Promise<RoadSegment[]> {
    if (useMock) return mockRoadSegments;
    const { data } = await client.get<RoadSegment[]>('/api/v1/segments/geojson');
    return data;
  }
  ```
  And `src/types/roadSegments.ts` defines `RoadSegment` as a flat object with `geometry: [number, number][]`.
- **Failure Mode:**  
  When `VITE_USE_MOCK=false`, `fetchSegments()` receives the `FeatureCollection` object. Components in `App.tsx` immediately execute `segments.map(...)` or `segments.filter(...)`, throwing an uncaught TypeError: **`TypeError: segments.map is not a function`**, completely crashing the React dashboard.
- **Remediation:**  
  1. In `src/services/api.ts`, update `fetchSegments` to call `/api/v1/segments/geojson?format=flat` OR unpack the GeoJSON `features`:
     ```ts
     const { data } = await client.get<any>('/api/v1/segments/geojson');
     if (Array.isArray(data)) return data;
     if (data?.features) {
       return data.features.map((f: any) => ({
         segment_id: f.properties.segment_id,
         name: f.properties.name,
         geometry: f.geometry.coordinates,
         condition_score: f.properties.condition_score,
         confidence: f.properties.confidence,
         pothole_count: f.properties.pothole_count,
         waterlogging_count: f.properties.waterlogging_count,
         observation_count: f.properties.observation_count,
         last_updated: f.properties.last_updated,
       }));
     }
     ```

---

### BUG-002: Incident Metric Discrepancy: `incident_score` vs `severity`

- **Severity:** `CRITICAL`
- **Affected Files:**
  - `src/types/incidents.ts` (Line 4)
  - `src/data/mockIncidents.ts` (Line 7, 19, 31)
  - `src/components/Details/IncidentInspector.tsx`
  - `backend/app/schemas/incidents.py` (Line 8–9)
  - `docs/API_CONTRACT.md` (Section 2.4)
- **Problem Description:**  
  `docs/API_CONTRACT.md` and the backend `IncidentResponse` define incidents with a discrete integer severity metric:
  `severity: int` ($1$ to $4$) and `severity_label: Optional[str]` (`"low"`, `"moderate"`, `"high"`, `"critical"`).  
  In contrast, the frontend `src/types/incidents.ts` defines:
  ```ts
  export interface Incident {
    incident_id: string;
    incident_type: string;
    incident_score: number; // e.g. 0.87
    ...
  }
  ```
- **Failure Mode:**  
  When live backend data is loaded, `incident.incident_score` is `undefined`. The Incident Inspector badge renders as blank or NaN, and the user cannot filter or view severity ratings for traffic violations.
- **Remediation:**  
  1. Update `src/types/incidents.ts` to include `severity: number` (1-4), `severity_label?: string`, and keep `incident_score?: number` for backward-compatibility.
  2. Update `backend/app/schemas/incidents.py` to optionally provide `incident_score` (aliased to confidence or computed from severity) so both schemas are mutually compatible.

---

### BUG-003: Database Schema Dual-State / Column Naming Discrepancy

- **Severity:** `CRITICAL`
- **Affected Files:**
  - `backend/scripts/migrate_to_documented_schema.sql`
  - `backend/scripts/migrate_schema.sql`
  - `backend/app/models/*.py`
  - `backend/app/api/v1/segments.py`
  - `docs/DATABASE_SCHEMA.md`
- **Problem Description:**  
  The Supabase PostgreSQL database was provisioned before `docs/DATABASE_SCHEMA.md` was finalized. It used legacy column names:
  - `buses`: `id` (UUID), `vehicle_number`, `last_ping`
  - `road_segments`: `id` (UUID), `road_name`, `health_score`, `geometry` (GEOMETRY)
  - `observations`: `id` (UUID), `road_segment_id`, `observation_type`, `location`, `detected_at`, `evidence_path`
  - `incidents`: `id` (UUID), `location`, `detected_at`
  - `segment_history`: `id` (UUID), `road_segment_id`, `health_score`
  - `gps_points`: `id` (UUID), `location`, `heading`, `speed`

  The backend models (`backend/app/models/`) and SQL queries in `segments.py` query **canonical names** (`segment_id`, `geom`, `condition_score`, `last_updated`, `event_type`, `observed_at`).
  If a developer or production environment runs the older, partial script `backend/scripts/migrate_schema.sql`, the canonical columns are **never created**.
- **Failure Mode:**  
  Running the backend against a database with only `migrate_schema.sql` applied causes immediate SQL execution errors:  
  `asyncpg.exceptions.UndefinedColumnError: column "segment_id" does not exist`.
- **Remediation:**  
  1. Mandate the execution of `backend/scripts/migrate_to_documented_schema.sql`, which safely and non-destructively reconciles the schema within a transaction without dropping legacy columns.
  2. Update `backend/README.md` and `docs/ENVIRONMENT.md` to deprecate `migrate_schema.sql` and highlight `migrate_to_documented_schema.sql` as the required migration.

---

### BUG-004: Frontend WebSocket Client Disconnected from UI State

- **Severity:** `HIGH`
- **Affected Files:**
  - `src/services/websocket.ts`
  - `src/pages/Dashboard.tsx`
  - `src/App.tsx`
- **Problem Description:**  
  `backend/app/websocket/live.py` and `backend/app/websocket/manager.py` implement real-time streaming of `BUS_TELEMETRY` and `NEW_EVENT` frames to all clients connected at `/ws/live`.  
  `src/services/websocket.ts` defines stub functions `connectWebSocket` and `disconnectWebSocket`.  
  However, **neither function is imported or called anywhere in the frontend codebase**.
- **Failure Mode:**  
  The dashboard operates purely in static REST polling/hydration mode. Moving fleet buses do not animate or update coordinates, and newly detected road defects do not appear in real-time.
- **Remediation:**  
  Implement a `useLiveStream` hook in `src/services/websocket.ts` (or connect in `Dashboard.tsx`) that updates the `buses` state and prepends new defect events to the `events` state when `BUS_TELEMETRY` and `NEW_EVENT` messages arrive.

---

### BUG-005: Map-Matching PostGIS Fallback Query Schema Qualification Flaw

- **Severity:** `HIGH`
- **Affected Files:**
  - `backend/app/services/map_matching.py` (Lines 59–75)
- **Problem Description:**  
  In `find_nearest_road_segment`, the primary query correctly qualifies PostGIS functions using `{gis_schema}.ST_Distance` and `{gis_schema}.ST_DWithin`.  
  However, in the `except Exception:` fallback block (lines 59–75), the SQL string calls:
  ```sql
  ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography)
  ```
  without the schema qualifier.
- **Failure Mode:**  
  In Supabase, PostGIS extensions are frequently installed in the `gis` schema and `gis` is not on the default connection `search_path`. If the primary query triggers an error, the fallback query fails with:  
  `function st_makepoint(unknown, unknown) does not exist`.
- **Remediation:**  
  Either remove the duplicate unqualified fallback or ensure the fallback query properly sets `SET search_path TO public, gis;` before running.

---

### BUG-006: Segment History Multi-Insert Duplication on Bulk Ingestion

- **Severity:** `HIGH`
- **Affected Files:**
  - `backend/app/services/aggregation.py` (Lines 79–91)
  - `backend/app/services/ingestion.py` (Line 131)
- **Problem Description:**  
  When an observation is ingested via `POST /api/v1/observations`, `recalculate_segment_metrics` is invoked immediately. It recalculates the segment score and creates a new `SegmentHistory` record with `recorded_at = now_utc`.  
  When a bus passes through a road segment and detects 10 potholes or cracks within 30 seconds, 10 distinct `SegmentHistory` records are inserted with virtually identical timestamps and condition scores.
- **Failure Mode:**  
  The `recharts` historical condition timeline in `RoadInspector.tsx` gets flooded with dozens of redundant microsecond data points, degrading chart readability and wasting database storage.
- **Remediation:**  
  Implement a debouncing window or minimum time interval (e.g., only create a `SegmentHistory` snapshot if no history entry was created for this segment within the last 15 minutes, or update the existing snapshot within the active hour).

---

### BUG-007: Evidence Signed URL Expiration Causes Broken Media in UI

- **Severity:** `HIGH`
- **Affected Files:**
  - `backend/app/services/evidence.py` (Lines 38, 47)
  - `src/components/Details/EventInspector.tsx`
  - `src/components/Details/IncidentInspector.tsx`
- **Problem Description:**  
  `evidence.py` generates temporary signed URLs using `create_signed_url(storage_path, 3600)`.  
  The signed URL is valid for only 3,600 seconds (1 hour). When stored in the `observations` or `incidents` table and later fetched by the frontend via `GET /api/v1/events` after 1 hour, the URL has expired (`403 Signature Expired`).
- **Failure Mode:**  
  Evidence image previews fail to load with HTTP 403 errors, showing broken image icons to municipal operators.
- **Remediation:**  
  1. Store canonical storage paths (`uploads/evt_123.jpg`) in the database.
  2. Implement an on-demand endpoint `GET /api/v1/evidence/sign?path=...` or generate a signed URL dynamically with a 24-hour expiration upon API response serialization.

---

### BUG-008: Segment ID Formatting Inconsistency (Hyphen vs Underscore)

- **Severity:** `MEDIUM`
- **Affected Files:**
  - `src/data/mockRoadSegments.ts` (`seg-chd-001`, `seg-chd-002`)
  - `src/data/mockIncidents.ts` (`seg-chd-001`)
  - `backend/scripts/test_ingestion.py` (`seg_chandigarh_001`)
  - `docs/API_CONTRACT.md` (`seg_chandigarh_001`)
- **Problem Description:**  
  Frontend mock data uses hyphenated prefixes (`seg-chd-001`), whereas `API_CONTRACT.md`, backend test scripts, and canonical database seeds use underscore notation (`seg_chandigarh_001`).
- **Failure Mode:**  
  If the frontend runs in mixed mock/live testing mode, lookups like `mockSegmentHistory[segmentId]` fail with empty arrays because the keys do not match.
- **Remediation:**  
  Standardize all segment IDs across mock data, seeds, and documentation to `seg_chandigarh_001` format.

---

### BUG-009: SQLite In-Memory Database Fallback Incompatible with PostGIS

- **Severity:** `MEDIUM`
- **Affected Files:**
  - `backend/app/db/database.py` (Lines 16–23)
- **Problem Description:**  
  `database.py` has a fallback:
  ```python
  if "asyncpg" in db_url:
      try:
          import asyncpg
      except ImportError:
          db_url = "sqlite+aiosqlite:///:memory:"
  ```
  However, the backend routes (`app/api/v1/segments.py`, `app/services/map_matching.py`) execute raw PostGIS SQL queries (`ST_AsGeoJSON`, `ST_DWithin`, `ST_Distance`).
- **Failure Mode:**  
  If `asyncpg` is missing or PostgreSQL is unavailable, attempting to start the server and query `/api/v1/segments/geojson` raises SQLite syntax errors (`no such function: ST_AsGeoJSON`).
- **Remediation:**  
  Remove the silent SQLite fallback or fail fast with a clear error: `"PostgreSQL with PostGIS is required. Cannot fall back to SQLite for spatial queries."`

---

### BUG-010: Missing WebSocket Auto-Reconnection & Backoff in Frontend

- **Severity:** `MEDIUM`
- **Affected Files:**
  - `src/services/websocket.ts` (Lines 19–20)
- **Problem Description:**  
  In `websocket.ts`, the `onclose` handler simply resets `socket = null`:
  ```ts
  socket.onclose = () => { socket = null; };
  ```
  There is no exponential backoff, retry loop, or heartbeat monitor.
- **Failure Mode:**  
  Any transient network blip, backend restart, or mobile vehicle Wi-Fi disconnection permanently disables live updates until the user manually reloads the browser.
- **Remediation:**  
  Implement an auto-reconnect strategy with exponential backoff (1s, 2s, 5s, 10s, max 30s) and a 30-second ping heartbeat.

---

### BUG-011: Contradictory Database Migration Instructions in Documentation

- **Severity:** `MEDIUM`
- **Affected Files:**
  - `backend/README.md` (Section 5, lines 122–141)
  - `docs/DATABASE_SCHEMA.md`
- **Problem Description:**  
  `backend/README.md` Section 5 stated:
  *"DO NOT RECREATE TABLES IN SUPABASE! ... Copy and execute scripts/migrate_schema.sql"*.  
  However, `migrate_schema.sql` does NOT add the canonical primary keys or column renames (`segment_id`, `geom`, `event_type`, `observed_at`), whereas `backend/scripts/migrate_to_documented_schema.sql` (1273 lines) was created specifically for this safe migration.
- **Failure Mode:**  
  New developers following `backend/README.md` execute the wrong SQL script and experience database errors.
- **Remediation:**  
  Update `backend/README.md` to instruct running `backend/scripts/migrate_to_documented_schema.sql` directly.

---

### BUG-012: Event Query Parameter Type Coercion (`min_severity`)

- **Severity:** `MEDIUM`
- **Affected Files:**
  - `backend/app/api/v1/events.py` (Line 20)
  - `src/services/api.ts`
  - `src/types/filters.ts`
- **Problem Description:**  
  `backend/app/api/v1/events.py` defines `min_severity: Optional[int] = Query(default=None, ge=1, le=4)`.  
  If the frontend passes string severity values (e.g. `"critical"` or `"high"`), FastAPI raises HTTP 422 Unprocessable Entity.
- **Failure Mode:**  
  Filter panel requests fail if parameter types are not strictly cast to integers before sending query strings.
- **Remediation:**  
  Ensure frontend passes `min_severity` as integer `1, 2, 3, 4` and backend accepts both string and integer representations gracefully.

---

### BUG-013: Hardcoded Absolute Machine File Links in Project Documentation

- **Severity:** `LOW`
- **Affected Files:**
  - `AGENT_CONTEXT.md`
  - `docs/TECH_STACK.md`
  - `docs/ARCHITECTURE.md`
  - `docs/AGENT_STATE.md`
  - `docs/MODULE_OWNERSHIP.md`
- **Problem Description:**  
  Over 20 markdown links contained hardcoded paths to a previous developer's machine:
  `file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/...`
- **Failure Mode:**  
  Clicking documentation links in VS Code or GitHub returns 404 or points to non-existent local machine locations.
- **Remediation:**  
  Convert all absolute machine URI links to standard relative markdown links (e.g., `docs/API_CONTRACT.md` or `[API_CONTRACT.md](API_CONTRACT.md)`).

---

### BUG-014: Missing Automated Integration Tests for Live API Hydration

- **Severity:** `LOW`
- **Affected Files:**
  - `backend/tests/test_api_routes.py`
  - `src/tests/` (missing)
- **Problem Description:**  
  The backend test suite mocks the database session, and the frontend currently relies purely on compile-time TypeScript type checking without contract tests comparing frontend JSON deserialization against backend endpoint serialization.
- **Failure Mode:**  
  Schema drift (such as BUG-001 and BUG-002) goes undetected by automated test suites until manual end-to-end testing.
- **Remediation:**  
  Add automated contract tests or a mock API server test in the test suite that asserts frontend type compatibility.

---

## 4. Prioritized Action Matrix

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Immediate Critical Fixes (Pre-requisite for Live Demo)         │
│  [x] Document all bugs & discrepancies in BUGS_AND_DISCREPANCIES.md     │
│  [ ] Update src/services/api.ts to handle FeatureCollection & flat fmt │
│  [ ] Add severity/severity_label to src/types/incidents.ts             │
│  [ ] Execute backend/scripts/migrate_to_documented_schema.sql on DB   │
├────────────────────────────────────────────────────────────────────────┤
│ Phase 2: Live Streaming & Resilience                                   │
│  [ ] Connect frontend WebSocket listener in Dashboard.tsx              │
│  [ ] Add auto-reconnect backoff to src/services/websocket.ts           │
│  [ ] Add debouncing to segment_history generation in aggregation.py    │
├────────────────────────────────────────────────────────────────────────┤
│ Phase 3: Documentation & Contract Synchronization                       │
│  [x] Eliminate all hardcoded machine URI links in docs/                │
│  [x] Synchronize API_CONTRACT.md, AI_CONTRACT.md, and DATABASE_SCHEMA   │
│  [x] Update AGENT_CONTEXT.md and AGENT_STATE.md                        │
└────────────────────────────────────────────────────────────────────────┘
```
