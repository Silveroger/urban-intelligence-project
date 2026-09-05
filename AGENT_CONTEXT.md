# SIH 26124 — Agent Operating Context

## 1. Executive Purpose & Authority
This document is the authoritative, compact project context and executive briefing for AI agents working in this repository. It provides the essential context, engineering constraints, and conventions required before modifying code.

Detailed domain specifications are strictly owned by their designated documents in `docs/` (see Section 6).

---

## 2. Project Mission & Core Philosophy
**Problem:** SIH 26124 — AI-Powered Mobile Urban Intelligence Platform Using Public Transport Fleet.

- **Core Concept:** City buses and test vehicles act as mobile sensing nodes. Camera sensors and GPS feeds capture edge data $\to$ specialized computer vision models detect road defects and traffic events $\to$ backend spatial engine matches observations and aggregates repeated passes $\to$ persistent road health state is maintained in PostGIS $\to$ visualized on the decision-support GIS dashboard.
- **Key Differentiator:** The platform focuses on **repeated geospatial observations and persistent road health state**, rather than single-image evaluations or generic chatbot interfaces.

---

## 3. Subsystem Ownership & Boundaries
- **GIS Frontend Dashboard (`src/`):** Led by Eshan.
  - **Frontend Owns:** Map rendering, vector polylines, Advanced Markers, deck.gl heatmap overlays, multi-tier filters, segment/event/incident inspector drawers, historical degradation charts, and responsive UI state.
  - **Frontend Does NOT Own:** Machine learning model training, client-side AI inference, GPS road-matching algorithms, PostGIS spatial indexing, or multi-pass condition score computation. The frontend visualizes the backend's persistent urban state.
- **Backend & Geospatial Ingestion (`backend/`):** Led by Aryush Butar.
  - **Backend Owns:** FastAPI async services, PostGIS spatial indexing, GPS map-matching (`ST_DWithin`), multi-pass score aggregation, REST/WebSocket API endpoints (`/api/v1/*`, `/ws/live`), Supabase Storage evidence integration, and database schema migrations.
  - **Backend Does NOT Own:** Client-side React rendering or edge computer vision model training.
- **Full Team Ownership:** Documented in [`docs/MODULE_OWNERSHIP.md`](docs/MODULE_OWNERSHIP.md).

---

## 4. Critical Engineering Conventions & Constraints
1. **Coordinate Format Boundary:**
   - Spatial data interchange and storage strictly use GeoJSON `[longitude, latitude]` (EPSG:4326).
   - Google Maps JavaScript API requires `{lat, lng}` objects.
   - All transformations are isolated to `src/utils/coordinates.ts` (`geoJsonToGooglePath`). Never manually invert coordinates in ad-hoc components.
2. **Telemetry Speed Constraint:**
   - Vehicle speed is **optional** in prototype telemetry. Bus telemetry requires only `bus_id`, `timestamp`, `latitude`, `longitude`, and optional `heading_deg`.
3. **Data Layer Abstraction:**
   - The UI never imports mock data directly into presentation components. All data access occurs via `src/services/api.ts` and `src/services/websocket.ts`.
   - `VITE_USE_MOCK=true` allows full offline development and testing.
4. **Heatmap Technology:**
   - Google Maps native `HeatmapLayer` is deprecated. Use `@deck.gl/google-maps` and `@deck.gl/aggregation-layers` inside `DeckHeatmapOverlay.tsx`.
5. **OCR Plate Text Caution:**
   - Detected license plate strings must always be presented alongside their `plate_confidence` score. Never present raw OCR as absolute ground truth.
6. **PostGIS Schema Qualification:**
   - In Supabase, PostGIS spatial functions are located in the `gis` schema. Backend raw queries and DDL must qualify functions with `gis.` or ensure `gis` is included in the connection search path.
7. **Database Migration Safety:**
   - Schema modifications must be non-destructive and transactional. Use [`backend/scripts/migrate_to_documented_schema.sql`](backend/scripts/migrate_to_documented_schema.sql) to safely reconcile legacy database states.

---

## 5. Agent Behavioral & Code Style Rules
- **Inspect Before Modifying:** Understand existing files, props, and types before making changes.
- **Smallest Correct Change:** Prefer surgical, minimal edits over broad rewrites. Keep files concise and maintainable.
- **No Inventions:** Do not invent backend endpoints, database fields, or schemas without updating the relevant contract documents.
- **Zero Token Waste:** Do not write redundant boilerplate, duplicate utility functions, or add libraries when existing dependencies suffice.
- **Verification Mandatory:** Always run `npm run lint` and `npm run build` after changes. Verify that the app remains functional.

---

## 6. Authoritative Documentation Hierarchy

Every category of project information has exactly ONE authoritative document:

| Category | Authoritative Document | Contents & Scope |
|---|---|---|
| **1. Agent Context** | `AGENT_CONTEXT.md` *(this file)* | Executive project briefing, critical constraints, agent operating rules. |
| **2. Product Requirements** | [`docs/PRD.md`](docs/PRD.md) | Problem statement, user personas, P0/P1/P2 feature scope, acceptance criteria, non-goals. |
| **3. Tech Stack** | [`docs/TECH_STACK.md`](docs/TECH_STACK.md) | Libraries, versions, infrastructure, and technology-specific purposes. |
| **4. Architecture** | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | End-to-end data pipeline, subsystem boundaries, integration architecture. |
| **5. API Contract** | [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) | REST endpoints, WebSocket frame formats, JSON schemas, error codes. |
| **6. AI Contract** | [`docs/AI_CONTRACT.md`](docs/AI_CONTRACT.md) | AI perception structured output schemas, defect classes, confidence rules. |
| **7. Database Schema** | [`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md) | PostgreSQL + PostGIS spatial schema, tables, geometry types, spatial indexing. |
| **8. Module Ownership** | [`docs/MODULE_OWNERSHIP.md`](docs/MODULE_OWNERSHIP.md) | Team subsystem ownership, paths, and cross-boundary collaboration policies. |
| **9. Decisions (ADRs)** | [`docs/DECISIONS.md`](docs/DECISIONS.md) | Architectural Decision Records (ADR-001 through ADR-010) and rationale. |
| **10. Agent State** | [`docs/AGENT_STATE.md`](docs/AGENT_STATE.md) | Temporary implementation baseline, active milestones, and known blockers. |
| **11. Backlog** | [`docs/BACKLOG.md`](docs/BACKLOG.md) | Prioritized backlog tasks across P0, P1, and P2 tiers. |
| **12. Environment** | [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) | Local development setup, npm scripts, and environment variable configuration. |
| **13. Security** | [`docs/SECURITY.md`](docs/SECURITY.md) | Security baseline, secrets handling, API key restrictions, CORS, and data privacy. |
| **14. Testing** | [`docs/TESTING.md`](docs/TESTING.md) | Multi-tier testing strategy, verification commands, and Definition of Done. |
| **15. Frontend Architecture** | [`docs/FRONTEND_ARCHITECTURE.md`](docs/FRONTEND_ARCHITECTURE.md) | Directory structure, state separation, map lifecycle, and color threshold rules. |
| **16. Bugs & Discrepancies** | [`docs/BUGS_AND_DISCREPANCIES.md`](docs/BUGS_AND_DISCREPANCIES.md) | Comprehensive defect, discrepancy, and remediation register across all subsystems. |
