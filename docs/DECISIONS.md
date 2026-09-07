# Architectural Decision Records (ADRs)

## ADR-001 — PostgreSQL + PostGIS for Spatial Persistence
- **Status:** Accepted
- **Context:** The platform requires persistent storage for road geometries, vehicle GPS traces, and spatial multi-pass observation matching.
- **Decision:** Use PostgreSQL with the PostGIS extension as the primary spatial datastore. Structured relational attributes are indexed alongside spatial geometry columns (`GEOMETRY(LineString, 4326)` and `GEOMETRY(Point, 4326)`), utilizing GiST indexing.
- **Consequence:** Spatial indexing and map-matching logic remain centralized on the backend rather than burdening the frontend.

---

## ADR-002 — Frontend Data Provider & Mock Abstraction
- **Status:** Accepted
- **Context:** Frontend development and testing must proceed smoothly without requiring active edge hardware or live backend servers.
- **Decision:** Implement a centralized data provider in `services/api.ts` governed by `VITE_USE_MOCK=true/false`. The mock provider adheres to identical TypeScript interfaces as the live REST/WebSocket APIs.
- **Consequence:** UI presentation components consume typed domain data without awareness of whether the underlying source is mock data or live backend endpoints.

---

## ADR-003 — GeoJSON Coordinate Order Standard
- **Status:** Accepted
- **Context:** GeoJSON and deck.gl use `[longitude, latitude]` order (EPSG:4326), whereas the Google Maps JavaScript API expects `{lat, lng}` object format. Inconsistent transformations cause projection and polyline rendering defects.
- **Decision:** All API interchange payloads, mock datasets, and database entities strictly use GeoJSON `[lng, lat]` order. Transformations to `{lat, lng}` are isolated to a single utility function (`geoJsonToGooglePath`) executed exclusively at map rendering boundaries.
- **Consequence:** Eliminates repeated, ad-hoc coordinate conversions across individual React components.

---

## ADR-004 — REST State Hydration + WebSocket Delta Streaming
- **Status:** Accepted
- **Context:** The dashboard requires fast initial load times for complete city networks while supporting real-time telemetry updates.
- **Decision:** Use REST endpoints for initial bulk state hydration (road polylines, active markers, KPI totals) and WebSocket (`/ws/live`) for high-frequency deltas (bus GPS pings, newly confirmed defects).
- **Consequence:** If WebSocket connection drops, the application remains fully functional and informative with cached REST data.

---

## ADR-005 — Specialized Computer Vision over Generic LLMs
- **Status:** Accepted
- **Context:** SIH problem statement focuses on automated urban sensing and infrastructure quality assessment.
- **Decision:** The core perception engine uses specialized computer vision models (YOLO / segmentation networks) optimized for pothole detection, waterlogging classification, and vehicle tracking. Generic conversational chatbots are not part of the core product architecture.
- **Consequence:** Resources remain focused on high-precision spatial detection, repeated-observation scoring, and actionable decision-support tools.

---

## ADR-006 — deck.gl Overlays for Heatmap Visualization
- **Status:** Accepted
- **Context:** Google Maps JavaScript API has deprecated its native `HeatmapLayer`.
- **Decision:** Use `@deck.gl/google-maps` and `@deck.gl/aggregation-layers` (`HeatmapLayer`) for rendering dense traffic and defect heatmaps directly over the Google Maps vector basemap.
- **Consequence:** High-performance GPU-accelerated heatmap rendering without relying on deprecated Google Maps libraries.

---

## ADR-007 — Optional Bus Speed in Telemetry
- **Status:** Accepted
- **Context:** Prototype fleet hardware may provide intermittent or uncalibrated vehicle speed readings.
- **Decision:** Vehicle speed is treated as an optional field in telemetry models. Core map rendering, road scoring, and event markers must function completely without requiring speed values.
- **Consequence:** Simplifies hardware integration and prevents prototype failures caused by missing speed telemetry.

---

## ADR-008 — PostGIS Functions in Dedicated `gis` Schema
- **Status:** Accepted
- **Context:** In managed Supabase PostgreSQL instances, the PostGIS extension is installed under the `gis` schema rather than `public`.
- **Decision:** All raw spatial SQL queries, map-matching functions, and index creation statements must explicitly reference functions with the schema qualifier (e.g., `{gis_schema}.ST_DWithin`, `{gis_schema}.ST_Distance`, `{gis_schema}.ST_MakePoint`, `{gis_schema}.ST_AsGeoJSON`).
- **Consequence:** Ensures predictable spatial query execution across local Docker, test runners, and managed cloud databases without requiring superuser alterations to global `search_path`.

---

## ADR-009 — Non-Destructive Schema Reconciliation
- **Status:** Accepted
- **Context:** The database was provisioned before canonical entity names were established, resulting in naming mismatches with contract documents. Recreating tables would wipe valuable edge calibration data.
- **Decision:** Execute [`backend/scripts/migrate_to_documented_schema.sql`](../backend/scripts/migrate_to_documented_schema.sql) which adds canonical columns and foreign key constraints within a single transaction while preserving legacy UUIDs and columns as auxiliary attributes.
- **Consequence:** Seamless transition to canonical contracts with zero data loss.

---

## ADR-010 — Integer Severity Storage with Display Label Aliases
- **Status:** Accepted
- **Context:** Perception models and edge annotators emit varying severity representations (numeric $1-4$ vs text strings like `"high"`, `"critical"`).
- **Decision:** The database and internal scoring engines strictly store severity as `SMALLINT` ($1-4$). API responses serialize both `severity` (integer) and `severity_label` (string) for convenient frontend presentation.
- **Consequence:** Efficient mathematical calculations in the scoring engine while maintaining readable badges on dashboard cards.

---

## ADR-011 — Supabase Regional IPv4 Session Pooler Connectivity on Windows
- **Status:** Accepted
- **Context:** Direct database endpoints (`db.<project-ref>.supabase.co:5432`) only advertise IPv6 (AAAA) DNS records in AWS regions. On Windows environments without native IPv6 routing, connecting caused fatal runtime crashes with `[Errno 11001] getaddrinfo failed`.
- **Decision:** Route all backend database connections via Supabase's regional IPv4 Session Pooler (`aws-0-ap-northeast-2.pooler.supabase.com:5432` or port `6543`) with `connect_args={"server_settings": {"search_path": "public, gis"}}`.
- **Consequence:** 100% reliable cross-platform database connectivity on both Windows and Linux without modifying operating system routing tables.

---

## ADR-012 — Canonical GPS Architecture (`gps_points` Physical Table with `gps_records` Compatibility View)
- **Status:** Accepted
- **Context:** Raw telemetry models were implemented writing to `gps_points`, while original database documentation referenced `gps_records`. Attempting to migrate live storage or maintain dual tables risked splitting telemetry into competing pipelines.
- **Decision:** Designate `public.gps_points` as the authoritative physical table for raw high-frequency GPS telemetry, and define `public.gps_records` as a zero-overhead compatibility view (`CREATE OR REPLACE VIEW gps_records AS SELECT * FROM gps_points;`).
- **Consequence:** Zero data loss, total backward-compatibility with documented contracts, and a clear architectural rule preventing developers from building competing GPS pipelines.

---

## ADR-013 — Elimination of SQLite Fallback & Strict HTTP 503 Database Error Gateway
- **Status:** Accepted
- **Context:** Earlier backend revisions silently fell back to an in-memory SQLite database upon connection failure, masking broken PostgreSQL credentials and crashing when executing PostGIS functions like `ST_AsGeoJSON` or `ST_DWithin`.
- **Decision:** Completely eliminate silent SQLite fallbacks. Enforce a fail-fast startup check that raises a `RuntimeError` if PostgreSQL or `asyncpg` is unavailable. Route all runtime database connection failures and query errors through custom FastAPI exception handlers returning HTTP 503 `DATABASE_CONNECTION_ERROR` without leaking connection secrets or internal hostnames.
- **Consequence:** Fail-fast reliability during startup and clean, secure contract-compliant error responses in production.

---

## ADR-014 — Confidence-Weighted Road Health Scoring and Clean-Pass Recovery
- **Status:** Accepted
- **Context:** Road condition scoring treated all confirmed defects equally regardless of detection confidence, and had no mechanism to restore road scores after repairs or confirmed clean passes.
- **Decision:** Implement confidence-weighted penalties in `calculate_road_health` (`penalty = base_weight * freq_multiplier * confidence`), support clean-pass recovery credits (+5.0 condition points per verified clean pass, up to 100.0 max), and debounce historical snapshots in `segment_history` to 10-second windows.
- **Consequence:** Highly accurate, self-healing condition scoring that rewards verified clean road inspections and prevents database bloat from rapid multi-detections.

---

## ADR-015 — OSM-Derived Canonical Road Geometries and WGS84 Spatial Alignment
- **Status:** Accepted
- **Context:** Initial demo and seed data used coarse synthetic lines (2-4 vertices per segment) that cut straight across Chandigarh sectors rather than following physical street centerlines on the Google Maps vector basemap.
- **Decision:** Extract authentic road centerlines from OpenStreetMap (OSM) for Chandigarh's primary arterial corridors (Jan Marg, Madhya Marg, Dakshin Marg, Purv Marg, Vigyan Marg, Sarovar Path, Himalaya Marg, Sukhna Path, Udyog Path, Vidya Path) with 13 to 38 vertices per segment. Persist the canonical dataset in `backend/data/chandigarh_roads_canonical.geojson` and seed into `public.road_segments.geom` in PostGIS as WGS84 (EPSG:4326) LineStrings. Snap all bus simulation routes, defect observations, and traffic incidents directly along these canonical centerlines (0.00m offset).
- **Consequence:** Eliminates disjointed lines and guarantees visual alignment with Google Maps basemap tiles, supports accurate map-matching, and establishes a permanent canonical road dataset that must never be overwritten with coarse synthetic lines.

---

## ADR-016 — Integration of Edge AI Pipeline via Thin Boundary Adapter (`BackendIngestAdapter`)
- **Status:** Accepted
- **Context:** Chirag's ML branch developed extensive computer vision detectors, tracking, edge optimization, and hardware receiving, alongside a duplicate in-memory backend that duplicated canonical FastAPI + PostGIS functionality.
- **Decision:** Preserve 100% of Chirag's computer vision detectors, trackers, GPS sync, edge optimizer, and hardware receiver. Discard the duplicate in-memory backend, duplicate spatial engine, duplicate aggregation, and direct Supabase GPS pipeline. Implement a thin translation boundary `BackendIngestAdapter` that normalizes edge events, translates taxonomy, enforces OCR rules, packs diagnostic metrics into PostgreSQL `observations.metadata` JSONB, and dispatches to canonical FastAPI endpoints (`/api/v1/telemetry`, `/api/v1/observations`, `/api/v1/incidents`).
- **Consequence:** Eliminates code duplication, maintains PostGIS as the single spatial source of truth, and unifies edge intelligence with canonical persistence.

---

## ADR-017 — Zero-Friction Local Development Startup Architecture
- **Status:** Accepted
- **Context:** Developers faced pathing and environment confusion launching the backend and frontend across different working directories and virtual environment locations. IDEs querying system Python reported unresolved imports.
- **Decision:** Standardize root-level orchestration via `start-dev.ps1` (with individual `start-backend.ps1` and `start-frontend.ps1` scripts, plus `.bat` alternatives). Bootstrap `sys.path` in `backend/__init__.py` and `backend/app/main.py` so the backend can run from repository root or `backend/`. Configure `.vscode/settings.json` and sync system Python so IDE analysis resolves cleanly across both `backend` and `ai` packages.
- **Consequence:** Developers can launch the entire stack with a single command (`.\start-dev.ps1`) from repository root with zero friction.
