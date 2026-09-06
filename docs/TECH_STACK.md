# Technology Stack & Infrastructure

## 1. Overview
This document specifies the authoritative technologies, libraries, runtime environments, and infrastructure components used across the SIH 26124 Urban Intelligence Platform.

---

## 2. Frontend Technologies (`src/`)

| Category | Technology | Version | Purpose & Architectural Role |
|---|---|---|---|
| **Core UI Framework** | `React` | `^19.2.8` | Declarative UI rendering, component state management, and virtual DOM reconciliation. |
| **Runtime & Bundler** | `Vite` | `^8.2.2` | Ultra-fast development server with Hot Module Replacement (HMR) and optimized Rollup production builds. |
| **Language** | `TypeScript` | `~6.0.2` | Static typing, contract enforcement across components and service layers, strict compile-time validation. |
| **Mapping Engine** | `@vis.gl/react-google-maps` | `^1.9.0` | React wrapper for Google Maps JavaScript API, handling map lifecycle, camera controllers, and vector map contexts. |
| **Map Base** | `Google Maps JS API (Vector)` | Latest | Vector Map ID support, hardware-accelerated 3D vector rendering, and `AdvancedMarkerElement`. |
| **Data Visualization** | `@deck.gl/google-maps` & `@deck.gl/aggregation-layers` | `^9.3.11` | High-performance WebGL/WebGPU overlay on Google Maps for rendering large-scale aggregate heatmaps (traffic density and defect concentrations). |
| **Charting Library** | `Recharts` | `^3.10.1` | Responsive SVG charts for road condition degradation trends, traffic statistics, and historical observation graphs. |
| **HTTP Client** | `Axios` | `^1.20.0` | Promise-based REST client for structured backend API requests, request/response interceptors, and error translation. |
| **Iconography** | `Lucide React` | `^1.37.0` | Comprehensive, consistent icon library for navigation, status indicators, and drawer controls. |
| **Styling & Design Tokens** | `Tailwind CSS` & `Vanilla CSS` | `^3.6.0` (tailwind-merge) | Dark-mode design system, glassmorphic panels, CSS custom properties, and responsive layout utilities. |
| **Code Quality & Linting** | `ESLint` & `typescript-eslint` | `^10.9.0` / `^8.67.0` | Static analysis, enforcement of React hooks rules, and project-wide TypeScript lint standards. |

---

## 3. Backend & Data Infrastructure (`backend/`)

| Category | Technology | Pinned Version | Purpose & Architectural Role |
|---|---|---|---|
| **Web Framework** | `FastAPI` | `>=0.110.0,<0.120.0` | Asynchronous REST endpoints, automated OpenAPI/Swagger documentation, and request validation. |
| **ASGI Web Server** | `Uvicorn[standard]` | `>=0.28.0,<0.35.0` | Lightning-fast ASGI production server handling concurrent async HTTP and WebSocket requests. |
| **Validation & Settings** | `Pydantic` & `Pydantic-Settings` | `>=2.6.0,<3.0.0` | Schema validation, environment variable parsing, and type coercion. |
| **ORM / Query Engine** | `SQLAlchemy[asyncio]` | `>=2.0.28,<2.1.0` | Async relational mapping, connection pooling, and transactional session management. |
| **Database Driver** | `asyncpg` | `>=0.31.0,<0.32.0` | High-performance asynchronous PostgreSQL database client with `search_path="public, gis"`. |
| **Spatial Extension** | `GeoAlchemy2` | `>=0.14.0,<0.16.0` | Spatial geometry integration with SQLAlchemy, supporting WKB/WKT and PostGIS types. |
| **Database & Auth Platform** | `Supabase` (Python SDK) | `>=2.3.0,<2.14.0` | PostgreSQL hosting, PostGIS geospatial functions, and Storage client management. |
| **Connection Pooling** | `Supabase Regional IPv4 Pooler` | AWS Seoul (ap-northeast-2) | Dedicated IPv4 session pooler (`aws-0-ap-northeast-2.pooler.supabase.com:5432`) resolving IPv6 DNS lookup failures on Windows (`[Errno 11001]`). |
| **Spatial Database Engine** | `PostgreSQL + PostGIS` | `17.6` / `3.3.7` | Authoritative persistent storage with PostGIS extension and types hosted in dedicated `gis` schema. |
| **Object Storage** | `Supabase Storage` | Latest (`road-evidence`) | Secure storage for defect crop frames and incident video clips with dynamic 1-hour signed URL access. |
| **Real-time Protocol** | `WebSockets` | `>=12.0,<14.0` | Native ASGI WebSocket streaming at `/ws/live` supporting `BUS_TELEMETRY`, `NEW_EVENT`, `NEW_INCIDENT`, and `SEGMENT_UPDATE`. |
| **Testing Framework** | `pytest` & `pytest-asyncio` | `>=8.0.0` / `>=0.23.5` | Async unit, route, schema, and live database integration test suite (40/40 passing tests). |

---

## 4. Edge & Sensing Stack

| Category | Technology | Purpose & Architectural Role |
|---|---|---|
| **Perception Models** | Specialized Computer Vision (YOLO/Custom) | Road defect detection (potholes, cracks), waterlogging detection, vehicle tracking, and optical character recognition (OCR) for license plates. |
| **Telemetry Hardware** | GPS Receiver + Camera Sensors | Captures vehicle coordinates, heading, and synchronized visual frames from public transport fleet buses. |
| **Edge Pre-Processing** | Python / C++ Edge Runtime | Samples video frames, executes lightweight inference or packages high-priority events, and uploads structured observation metadata. |

---

## 5. Technology Constraints & Decisions
- **No Deprecated Map Layers:** Google Maps deprecated `HeatmapLayer` is explicitly forbidden; `@deck.gl/google-maps` is the designated heatmap technology (see [`docs/DECISIONS.md`](DECISIONS.md)).
- **Coordinate Transformations & Canonical Geometries:** All spatial coordinates are stored and transmitted in GeoJSON `[longitude, latitude]` (EPSG:4326) and mapped to `{lat, lng}` solely at Google Maps rendering boundaries. Road centerlines use OpenStreetMap-derived canonical geometries (`chandigarh_roads_canonical.geojson`) with 13-38 vertices per segment.
- **PostGIS `gis` Schema:** PostGIS functions are hosted under the `gis` schema (e.g. `gis.ST_MakePoint`, `gis.ST_DWithin`, `gis.ST_Distance`, `gis.ST_AsGeoJSON`). Engine connection args configure `search_path="public, gis"` automatically.
- **Supabase Regional IPv4 Session Pooler:** On Windows or environments without native IPv6 routing, the pooler hostname (`aws-0-ap-northeast-2.pooler.supabase.com:5432`) is mandatory to prevent `[Errno 11001] getaddrinfo failed` errors.
- **Canonical GPS Architecture:** The physical storage table is `public.gps_points`. `public.gps_records` is maintained as a seamless, non-destructive compatibility `VIEW` (`SELECT * FROM public.gps_points;`). Creating duplicate tables or fragmented GPS pipelines is strictly forbidden.
- **Provider Abstraction & Live Default:** The frontend consumes data through `services/api.ts` and `services/websocket.ts`. Live production mode is enabled via `VITE_USE_MOCK=false`, with mock mode (`VITE_USE_MOCK=true`) available for offline testing.
