# Technology Stack & Infrastructure

## 1. Overview
This document specifies the authoritative technologies, libraries, runtime environments, and infrastructure components used across the SIH 26124 Urban Intelligence Platform.

---

## 2. Frontend Technologies (`urban-dashboard`)

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

## 3. Backend & Data Infrastructure

| Category | Technology | Target Version | Purpose & Architectural Role |
|---|---|---|---|
| **Application Server** | `FastAPI` (Python) | `3.11+` | Asynchronous REST endpoints and WebSocket server for high-throughput metadata ingestion and live client broadcasts. |
| **Spatial Database** | `PostgreSQL` + `PostGIS` | `15+` / `3.3+` | Authoritative persistent storage for spatial geometry (`GEOMETRY(LineString, 4326)`), spatial indexing (GiST), road matching, and multi-pass observation aggregation. |
| **Object Storage** | `S3-Compatible / MinIO` | Latest | Secure, scalable storage for evidence media, cropped defect frames, and incident clips referenced by URI. |
| **Transport Layer** | `REST (JSON) + WebSocket` | `HTTP/2` / `WSS` | REST for initial state hydration and historical queries; WebSocket (`/ws/live`) for real-time telemetry and event updates. |

---

## 4. Edge & Sensing Stack

| Category | Technology | Purpose & Architectural Role |
|---|---|---|
| **Perception Models** | Specialized Computer Vision (YOLO/Custom) | Road defect detection (potholes, cracks), waterlogging detection, vehicle tracking, and optical character recognition (OCR) for license plates. |
| **Telemetry Hardware** | GPS Receiver + Camera Sensors | Captures vehicle coordinates, heading, and synchronized visual frames from public transport fleet buses. |
| **Edge Pre-Processing** | Python / C++ Edge Runtime | Samples video frames, executes lightweight inference or packages high-priority events, and uploads structured observation metadata. |

---

## 5. Technology Constraints & Decisions
- **No Deprecated Map Layers:** Google Maps deprecated `HeatmapLayer` is explicitly forbidden; `@deck.gl/google-maps` is the designated heatmap technology (see [DECISIONS.md](file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/DECISIONS.md)).
- **Coordinate Transformations:** All spatial coordinates are stored and transmitted in GeoJSON `[longitude, latitude]` (EPSG:4326) and mapped to `{lat, lng}` solely at Google Maps rendering boundaries.
- **Provider Abstraction:** The frontend consumes data through `services/api.ts` and `services/websocket.ts`, enabling seamless switching between mock mode (`VITE_USE_MOCK=true`) and live backend endpoints without component modification.
