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
