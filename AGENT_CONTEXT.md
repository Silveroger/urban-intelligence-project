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
Eshan leads the **GIS Frontend Dashboard** (`urban-dashboard/src/`).

- **Frontend Owns:** Map rendering, vector polylines, Advanced Markers, deck.gl heatmap overlays, multi-tier filters, segment/event/incident inspector drawers, historical degradation charts, and responsive UI state.
- **Frontend Does NOT Own:** Machine learning model training, client-side AI inference, GPS road-matching algorithms, PostGIS spatial indexing, or multi-pass condition score computation. The frontend visualizes the backend's persistent urban state.
- **Full Team Ownership:** Documented in [MODULE_OWNERSHIP.md](file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/MODULE_OWNERSHIP.md).

---

## 4. Critical Engineering Conventions & Constraints
1. **Coordinate Format Boundary:**
   - Spatial data interchange and storage strictly use GeoJSON `[longitude, latitude]` (EPSG:4326).
   - Google Maps JavaScript API requires `{lat, lng}` objects.
   - All transformations are isolated to `src/utils/coordinates.ts` (`geoJsonToGooglePath`). Never manually invert coordinates in ad-hoc components.
2. **Telemetry Speed Constraint:**
   - Vehicle speed is **optional** in prototype telemetry. Bus telemetry requires only `bus_id`, `timestamp`, `latitude`, `longitude`, and optional `heading_deg`.
3. **Data Layer Abstraction:**
   - The UI never imports mock data directly. All data access occurs via `src/services/api.ts` and `src/services/websocket.ts`.
   - `VITE_USE_MOCK=true` allows full offline development and testing.
4. **Heatmap Technology:**
   - Google Maps native `HeatmapLayer` is deprecated. Use `@deck.gl/google-maps` and `@deck.gl/aggregation-layers` inside `DeckHeatmapOverlay.tsx`.
5. **OCR Plate Text Caution:**
   - Detected license plate strings must always be presented alongside their `plate_confidence` score. Never present raw OCR as absolute ground truth.

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
| **2. Product Requirements** | [PRD.md](file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/PRD.md) | Problem statement, user personas, P0/P1/P2 feature scope, acceptance criteria, non-goals. |
| **3. Tech Stack** | [TECH_STACK.md](file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/TECH_STACK.md) | Libraries, versions, infrastructure, and technology-specific purposes. |
| **4. Architecture** | [ARCHITECTURE.md](file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/ARCHITECTURE.md) | End-to-end data pipeline, subsystem boundaries, integration architecture. |
| **5. API Contract** | [API_CONTRACT.md](file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/API_CONTRACT.md) | REST endpoints, WebSocket frame formats, JSON schemas, error codes. |
| **6. AI Contract** | [AI_CONTRACT.md](file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/AI_CONTRACT.md) | AI perception structured output schemas, defect classes, confidence rules. |
| **7. Database Schema** | [DATABASE_SCHEMA.md](file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/DATABASE_SCHEMA.md) | PostgreSQL + PostGIS spatial schema, tables, geometry types, spatial indexing. |
| **8. Module Ownership** | [MODULE_OWNERSHIP.md](file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/MODULE_OWNERSHIP.md) | Team subsystem ownership, paths, and cross-boundary collaboration policies. |
| **9. Decisions (ADRs)** | [DECISIONS.md](file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/DECISIONS.md) | Architectural Decision Records (ADR-001 through ADR-007) and rationale. |
| **10. Agent State** | [AGENT_STATE.md](file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/AGENT_STATE.md) | Temporary implementation baseline, active milestones, and known blockers. |
| **11. Backlog** | [BACKLOG.md](file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/BACKLOG.md) | Prioritized backlog tasks across P0, P1, and P2 tiers. |
| **12. Environment** | [ENVIRONMENT.md](file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/ENVIRONMENT.md) | Local development setup, npm scripts, and environment variable configuration. |
| **13. Security** | [SECURITY.md](file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/SECURITY.md) | Security baseline, secrets handling, API key restrictions, CORS, and data privacy. |
| **14. Testing** | [TESTING.md](file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/TESTING.md) | Multi-tier testing strategy, verification commands, and Definition of Done. |
| **15. Frontend Architecture** | [FRONTEND_ARCHITECTURE.md](file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/FRONTEND_ARCHITECTURE.md) | Directory structure, state separation, map lifecycle, and color threshold rules. |
