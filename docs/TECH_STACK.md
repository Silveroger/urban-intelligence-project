# Technology Stack & Infrastructure

## 1. Overview
This document specifies the authoritative technologies, libraries, runtime environments, and infrastructure components used across the SIH 26124 Urban Intelligence Platform.

---

## 2. Frontend Technologies (`src/`)

| Category | Technology | Version | Purpose & Architectural Role |
|---|---|---|---|
| **Core UI Framework** | `React` | `^19.2.8` | Declarative UI rendering, component state management, and virtual DOM reconciliation. |
| **Runtime & Bundler** | `Vite` | `^8.2.2` | High-speed development server with Hot Module Replacement (HMR) and optimized Rollup production builds. |
| **Language** | `TypeScript` | `~6.0.2` | Static typing, contract enforcement across components and service layers, strict compile-time validation. |
| **Mapping Engine** | `@vis.gl/react-google-maps` | `^1.9.0` | React wrapper for Google Maps JavaScript API, handling map lifecycle, camera controllers, and vector map contexts. |
| **Map Base** | `Google Maps JS API (Vector)` | Latest | Vector Map ID support, hardware-accelerated 3D vector rendering, and `AdvancedMarkerElement`. |
| **Data Visualization** | `@deck.gl/google-maps`, `@deck.gl/aggregation-layers`, `@deck.gl/core` | `^9.3.11` | High-performance WebGL/WebGPU overlay on Google Maps for rendering large-scale aggregate heatmaps (traffic density and defect concentrations). |
| **Cloud & Realtime Client**| `@supabase/supabase-js` | `^2.112.4` | Direct client-side Supabase subscription to `gps_records`, `observations`, and `incidents` realtime channels. |
| **Charting Library** | `Recharts` | `^3.10.1` | Responsive SVG charts for road condition degradation trends, traffic statistics, and historical observation graphs. |
| **HTTP Client** | `Axios` | `^1.20.0` | Promise-based REST client for structured backend API requests, request/response interceptors, and error translation. |
| **Iconography** | `Lucide React` | `^1.37.0` | Icon library for navigation, status indicators, HUD controls, and drawer controls. |
| **Styling & Design Tokens** | `Tailwind CSS`, `tailwind-merge`, `clsx` | `^3.6.0` / `^2.1.1` | Dark-mode design system, glassmorphic panels, CSS custom properties, and responsive layout utilities. |
| **Code Quality & Linting** | `ESLint` & `typescript-eslint` | `^10.9.0` / `^8.67.0` | Static analysis, enforcement of React hooks rules, and project-wide TypeScript lint standards. |

---

## 3. Backend & Data Infrastructure (`backend/` & `supabase/`)

| Category | Technology | Target Version | Purpose & Architectural Role |
|---|---|---|---|
| **Application Server** | `FastAPI` (Python) | `0.110+` (Python 3.10+) | Asynchronous REST endpoints, background video processing workers, and WebSocket server. |
| **ASGI Server** | `Uvicorn` | `0.28+` | High-performance ASGI production server supporting async IO and WebSockets. |
| **Spatial Engine** | `Shapely` & `PostGIS` | `2.0+` / `3.3+` | Road-network centerline map-matching, Hausdorff trajectory distance, and spatial aggregation. |
| **Cloud Database** | `Supabase (PostgreSQL 15+)` | Latest | Managed PostgreSQL with PostGIS, Row Level Security (RLS), and Realtime publications. |
| **Static Evidence Server** | `FastAPI StaticFiles` | — | Serves cropped defect keyframes and incident clips under `/evidence`. |
| **Transport Layer** | `REST (JSON) + WebSocket` | `HTTP/1.1-2` / `WSS` | REST for initial state hydration and historical queries; WebSocket (`/ws/live`) for real-time telemetry and event updates. |

---

## 4. Edge AI & Sensing Stack (`ai/`)

| Category | Technology | Purpose & Architectural Role |
|---|---|---|
| **Computer Vision Core** | `OpenCV` (`opencv-python-headless`) | Video decoding, frame preprocessing, color-space filtering, morphological analysis, and desktop HUD rendering. |
| **Perception Models** | Specialized YOLO (YOLOv8n / YOLO 26n) | Object detection for road defects, potholes, vehicles, pedestrians, and infrastructure assets. |
| **Edge Optimization** | `ONNX Runtime` & `PyTorch` | FP16 half-precision and INT8 quantization for low-power edge SBC deployment (Raspberry Pi 5 / NVIDIA Jetson). |
| **Tracking Engine** | Custom Euclidean + IoU Vehicle Tracker | Multi-object tracking across video frames with velocity and trajectory anomaly detection. |
| **OCR Engine** | License Plate Recognizer | Edge optical character recognition with confidence scoring for traffic incident reporting. |
| **Telemetry Hardware** | GPS Receiver + Dashcam Sensor | High-frequency NMEA/JSON telemetry capture synchronized with video timestamps. |

---

## 5. Technology Constraints & Decisions
- **No Deprecated Map Layers:** Google Maps deprecated `HeatmapLayer` is explicitly forbidden; `@deck.gl/google-maps` is the designated heatmap technology (see [DECISIONS.md](DECISIONS.md)).
- **Coordinate Transformations:** All spatial coordinates are stored and transmitted in GeoJSON `[longitude, latitude]` (EPSG:4326) and mapped to `{lat, lng}` solely at Google Maps rendering boundaries.
- **Provider Abstraction:** The frontend consumes data through `services/api.ts`, `services/websocket.ts`, and `services/supabase.ts`, enabling seamless switching between mock mode (`VITE_USE_MOCK=true`) and live backend endpoints without component modification.
