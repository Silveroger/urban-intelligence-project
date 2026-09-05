# Frontend Architecture

## 1. Directory Structure
The frontend application resides in `src/` and is organized as follows:

```text
src/
├── components/          # Focused, reusable presentation components
│   ├── Analytics/       # Charts, historical trends, traffic stats
│   ├── Cards/           # Metric cards (KPIs, status badges)
│   ├── Details/         # Inspection drawer panels (Road, Event, Incident)
│   ├── Map/             # Google Maps, Advanced Markers, Polylines, DeckHeatmapOverlay
│   └── Sidebar/         # Header, navigation, and FilterPanel
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
The UI never imports mock data directly into presentation components. All data requests flow through the service layer:

```text
┌──────────────────────────────┐
│  Mock Data (src/data/)       │ ──┐
└──────────────────────────────┘   │
                                   ▼
┌──────────────────────────────┐ ┌───────────────────────────┐
│  Live REST API               │─►│  src/services/api.ts      │
└──────────────────────────────┘  │  (VITE_USE_MOCK Switch)   │
                                  └─────────────┬─────────────┘
                                                │ Typed Models
                                                ▼
                                  ┌───────────────────────────┐
                                  │  Dashboard Page / State   │
                                  └─────────────┬─────────────┘
                                                │ Props
                                                ▼
                                  ┌───────────────────────────┐
                                  │  Map, Cards, Inspectors   │
                                  └───────────────────────────┘
```

---

## 4. Google Maps & deck.gl Lifecycle Management
- **Vector Base Map:** Managed via `@vis.gl/react-google-maps` using Google Cloud Vector Map ID.
- **Advanced Markers:** Rendered as child components inside `<Map>`, utilizing Google Maps `AdvancedMarkerElement` for crisp vector rendering.
- **deck.gl Overlay:** Encapsulated inside `DeckHeatmapOverlay.tsx`. Utilizes `useMap()` hook to acquire the Google Maps instance and hooks into the map lifecycle once via `GoogleMapsOverlay`, ensuring proper attachment and detachment upon unmount without memory leaks.

---

## 5. Coordinate Transformation Standard
All incoming and internal coordinates conform to GeoJSON `[longitude, latitude]`. The sole transformation to Google Maps `{lat, lng}` is performed by the canonical utility in `src/utils/coordinates.ts`:

```ts
export function geoJsonToGooglePath(coords: [number, number][]): { lat: number; lng: number }[] {
  return coords.map(([lng, lat]) => ({ lat, lng }));
}
```

---

## 6. Road-Health Color Thresholds
The frontend maps backend `condition_score` values ($0-100$) to visual status colors via `src/utils/roadColor.ts`:

| Condition Score Range | Status Tier | Color Name | Hex Code | Visual Meaning |
|---|---|---|---|---|
| $\ge 80.0$ | **Good** | Green | `#10b981` | Optimal road surface; no immediate action required. |
| $60.0 - 79.9$ | **Moderate** | Yellow / Amber | `#f59e0b` | Minor wear or early cracks; scheduled monitoring. |
| $40.0 - 59.9$ | **Poor** | Orange | `#f97316` | Significant degradation; maintenance required. |
| $< 40.0$ | **Critical** | Red | `#ef4444` | Severe potholes/waterlogging; urgent intervention. |

---

## 7. Performance & Rendering Guidelines
- **Stable Keys:** Always use unique entity IDs (`segment_id`, `event_id`, `bus_id`) as React `key` props. Never use array index for dynamic collections.
- **Isolated Telemetry:** Real-time bus marker position updates must not trigger re-rendering of static road polyline layers.
- **Memoized Calculations:** Use `useMemo` for computationally expensive filtering operations over large event datasets.
- **Contract Compatibility:** Active interface alignments with the backend (e.g., GeoJSON format handling and incident severity display) are cataloged in [`docs/BUGS_AND_DISCREPANCIES.md`](BUGS_AND_DISCREPANCIES.md).
