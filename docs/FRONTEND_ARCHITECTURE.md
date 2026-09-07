# Frontend Architecture

## 1. Directory Structure
The frontend application resides in `src/` and is organized as follows:

```text
src/
├── components/          # Focused, reusable presentation components
│   ├── Analytics/       # Charts, historical trends, traffic stats
│   ├── Cards/           # Metric cards (KPIs, status badges)
│   ├── Details/         # Inspection drawer panels (Road, Event, Incident, Civil Hazards)
│   ├── Map/             # Google Maps, Advanced Markers, Polylines, DeckHeatmapOverlay
│   ├── Sidebar/         # Header, navigation, and FilterPanel
│   └── VideoHub/        # Edge Video Processing Hub modal (VideoProcessingHub.tsx)
├── config/              # Centralized configuration (maps.ts, map IDs)
├── data/                # Typed mock datasets (mockRoadSegments, mockEvents, etc.)
├── pages/               # Top-level view composition (Dashboard.tsx)
├── services/            # Data layer abstractions (api.ts, websocket.ts)
├── types/               # TypeScript interfaces (roadSegments, events, buses, filters)
├── utils/               # Coordinate conversions, roadColor mapping, date formatters
├── App.tsx              # Application root
├── index.css            # Design tokens, Tailwind directives, dark mode styling
└── main.tsx             # React DOM entry point
```

---

## 2. Four-Way State Separation
To maintain responsiveness and prevent unnecessary re-renders, the frontend isolates state into four distinct domains:

```text
┌────────────────────────────────────────────────────────┐
│ 1. Backend Data State                                  │
│    (roadSegments, events, incidents, buses)            │
├────────────────────────────────────────────────────────┤
│ 2. Map Viewport State                                  │
│    (center, zoom, active layers: polylines, heatmap)   │
├────────────────────────────────────────────────────────┤
│ 3. Inspection UI State                                 │
│    (selectedSegment, selectedEvent, drawerOpen)        │
├────────────────────────────────────────────────────────┤
│ 4. Filter State                                        │
│    (eventTypes, minSeverity, conditionTiers, busIds)   │
└────────────────────────────────────────────────────────┘
```

---

## 3. Data Flow & Provider Layer
The UI never imports mock data directly into presentation components. All data requests flow through the service layer, with real-time deltas streamed over WebSockets:

```text
┌──────────────────────────────┐
│  Mock Data (src/data/)       │ ──┐ (Fallback if VITE_USE_MOCK=true)
└──────────────────────────────┘   │
                                   ▼
┌──────────────────────────────┐ ┌───────────────────────────┐
│  Live REST API               │─►│  src/services/api.ts      │
│  (Supabase + PostGIS via     │  │  (VITE_USE_MOCK=false)    │
│   FastAPI Endpoints)         │  └─────────────┬─────────────┘
└──────────────────────────────┘                │ Typed Models
                                                ▼
┌──────────────────────────────┐ ┌───────────────────────────┐
│  WebSocket (/ws/live)        │─►│  src/services/websocket.ts│
│  - BUS_TELEMETRY             │  │  (Auto-reconnect & PING)  │
│  - NEW_EVENT                 │  └─────────────┬─────────────┘
│  - NEW_INCIDENT              │                │ Real-Time Deltas
│  - SEGMENT_UPDATE            │                ▼
└──────────────────────────────┘  ┌───────────────────────────┐
                                  │  Dashboard Page / State   │
                                  └─────────────┬─────────────┘
                                                │ Props
                                                ▼
                                  ┌───────────────────────────┐
                                  │  Map, Cards, Inspectors   │
                                  └───────────────────────────┘
```

The live dashboard runs by default with **`VITE_USE_MOCK=false`**, hydrating all initial city infrastructure state from FastAPI endpoints and reacting immediately to live streaming frames.

---

## 4. Google Maps & deck.gl Lifecycle Management
- **Vector Base Map:** Managed via `@vis.gl/react-google-maps` using Google Cloud Vector Map ID.
- **Advanced Markers:** Rendered as child components inside `<Map>`, utilizing Google Maps `AdvancedMarkerElement` for crisp vector rendering.
- **deck.gl Overlay:** Encapsulated inside `DeckHeatmapOverlay.tsx`. Utilizes `useMap()` hook to acquire the Google Maps instance and hooks into the map lifecycle once via `GoogleMapsOverlay`, ensuring proper attachment and detachment upon unmount without memory leaks.

---

## 5. Coordinate Transformation Standard & Canonical Road Rendering
All incoming and internal coordinates conform to GeoJSON `[longitude, latitude]`. The sole transformation to Google Maps `{lat, lng}` is performed by the canonical utility in `src/utils/coordinates.ts`:

```ts
export function geoJsonToGooglePath(coords: [number, number][]): { lat: number; lng: number }[] {
  return coords.map(([lng, lat]) => ({ lat, lng }));
}
```

### Canonical Road Geometries on Vector Map
- **Authentic Road Curvature:** Road segment centerlines are OpenStreetMap-derived canonical geometries (`backend/data/chandigarh_roads_canonical.geojson`), containing 13 to 38 vertices per segment.
- **Visual Alignment:** Rendered as Google Maps `Polyline` vectors that accurately follow genuine physical streets across Chandigarh sectors (Jan Marg, Madhya Marg, Dakshin Marg, etc.), eliminating earlier straight synthetic shortcuts.
- **Payload Flexibility:** `fetchSegments()` in `src/services/api.ts` transparently normalizes both GeoJSON `FeatureCollection` and flat array formats.

---

## 6. Edge Video Processing Hub & Inspector Panels
- **Video Processing Hub (`src/components/VideoHub/VideoProcessingHub.tsx`):**  
  Accessible via the header button on `Dashboard.tsx`. Operators can initiate Edge AI perception scanning on test or uploaded dashcam videos, select active detection models (potholes, traffic density, plate OCR, pedestrians), and monitor real-time inference progress percentage.
- **Civil Hazard Inspector (`src/components/Details/Inspector.tsx`):**  
  When an operator clicks a road defect event, the inspector renders:
  - Defect category, timestamp, bus ID, and confidence percentage.
  - Civil engineering hazard metrics (estimated breadth in cm, depth in cm, and bounding area).
  - Risk assessment narrative and severity rating ($1-4$).
  - Cropped keyframe evidence image with signed URL caching.

---

## 7. Road-Health Color Thresholds
The frontend maps backend `condition_score` values ($0-100$) to visual status colors via `src/utils/roadColor.ts`:

| Condition Score Range | Status Tier | Color Name | Hex Code | Visual Meaning |
|---|---|---|---|---|
| $\ge 80.0$ | **Good** | Green | `#10b981` | Optimal road surface; no immediate action required. |
| $60.0 - 79.9$ | **Moderate** | Yellow / Amber | `#f59e0b` | Minor wear or early cracks; scheduled monitoring. |
| $40.0 - 59.9$ | **Poor** | Orange | `#f97316` | Significant degradation; maintenance required. |
| $< 40.0$ | **Critical** | Red | `#ef4444` | Severe potholes/waterlogging; urgent intervention. |

---

## 8. Performance & Error Handling Guidelines
- **Stable Keys:** Always use unique entity IDs (`segment_id`, `event_id`, `bus_id`, `incident_id`) as React `key` props. Never use array index for dynamic collections.
- **Isolated Telemetry:** Real-time bus marker position updates (`BUS_TELEMETRY`) update the bus state array and marker coordinates without triggering re-rendering of static road polyline layers.
- **Real-Time Map & Incident Sync:** When `SEGMENT_UPDATE` frames arrive, update the matching segment's `condition_score` and defect counts in place, instantly updating polyline color tiers. When `NEW_INCIDENT` frames arrive, prepend to active incidents and increment badge counts without full-page reloads.
- **WebSocket Reconnection & Heartbeats:** `src/services/websocket.ts` implements exponential backoff reconnection (1s, 2s, 5s, 10s, max 30s) and 30-second ping/pong heartbeats, ensuring persistent streaming through network blips or server restarts.
- **HTTP 503 Database Error Gateway:** The backend catches all database drops and emits standardized HTTP 503 `DATABASE_CONNECTION_ERROR`. The frontend Axios interceptor surfaces a non-blocking toast alert rather than failing uncaught.
- **Memoized Calculations:** Use `useMemo` for computationally expensive filtering operations over large event datasets.
- **Contract Compatibility:** All critical integration discrepancies (BUG-001 GeoJSON format, BUG-002 severity metric, BUG-004 WebSocket hookup, BUG-008 ID formatting, BUG-010 reconnect backoff, BUG-024 canonical road geometries) are verified resolved.
