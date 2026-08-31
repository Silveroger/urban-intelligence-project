# SIH 26124 — AGENT CONTEXT

## 0. Purpose
This file is the compact, persistent context for the SIH 26124 frontend/GIS work. Read this before changing code. The full team document is the authoritative project specification; this file is the implementation context for Eshan's dashboard.

## 1. Project
**Problem:** SIH 26124 — AI-Powered Mobile Urban Intelligence Platform Using Public Transport Fleet.

**Core idea:** buses/test vehicles act as mobile sensing nodes. Camera + GPS data -> specialized CV -> event metadata/evidence -> GPS/road matching -> repeated-observation aggregation -> persistent road/traffic/incident state -> GIS dashboard -> authority decisions.

**Differentiator:** repeated geospatial observations and persistent road state, not a generic chatbot or a single-image score.

## 2. Team / Eshan ownership
Eshan owns the **GIS frontend/dashboard**.

Frontend owns:
- map rendering
- road-condition visualization
- event markers
- traffic visualization
- incident visualization
- bus/GPS visualization
- filters
- segment/event inspection UI
- historical charts
- evidence display
- frontend state and interaction

Frontend does NOT own:
- AI inference
- model training
- map matching
- PostGIS logic
- road-condition scoring algorithm
- event aggregation logic
- backend truth

Backend provides persistent urban state; frontend visualizes it.

## 3. Current scope priorities
### P0 — implement first
- Road-health polylines
- Pothole/road-defect events
- Waterlogging events
- Traffic statistics
- Incident markers/details
- Bus/GPS positions
- Segment inspector
- Severity/confidence UI
- Historical pass observations
- Filters

### P1 — after P0 works
- Traffic-density heatmap via deck.gl
- Time scrubber / trip replay
- Evidence media inspection
- Maintenance-priority ranking
- Work-order export
- Fleet analytics

### P2 — future
- Missing zebra crossing/sign inference
- Route delay
- Origin-destination analytics

Do not implement P1/P2 before the P0 core loop is stable.

## 4. Current telemetry constraint
**Vehicle speed is NOT required for the current prototype.**

Current frontend bus telemetry:
- bus_id
- timestamp
- latitude
- longitude
- heading_deg (optional)

Do not make UI functionality depend on speed. Speed may be added later as an optional field without redesign.

## 5. Stack
- React
- TypeScript
- Vite
- ESLint
- Tailwind CSS
- Axios
- Recharts
- Lucide React
- `@vis.gl/react-google-maps`
- Google Maps JavaScript API
- Google Maps Advanced Marker Element
- deck.gl for later heatmaps

Backend:
- FastAPI
- PostgreSQL + PostGIS
- object storage
- REST + WebSocket

## 6. Existing setup
Project path:
`C:\Users\Eshan Sharma\Desktop\sih project\urban-dashboard`

Existing setup completed:
- Vite React + TypeScript project created
- ESLint selected
- frontend packages installed
- Google Maps API key exists
- Google Maps JavaScript Vector Map ID exists
- `.env` configured

Expected `.env` keys:
```env
VITE_GOOGLE_MAPS_API_KEY=...
VITE_GOOGLE_MAPS_MAP_ID=...
VITE_API_BASE_URL=http://localhost:8000
VITE_USE_MOCK=true
```

Never expose or print the API key. Never commit `.env`.

## 7. Required project structure
```text
src/
├── components/
│   ├── Map/
│   ├── Sidebar/
│   ├── Cards/
│   ├── Analytics/
│   ├── Details/
│   └── Evidence/
├── pages/
│   └── Dashboard.tsx
├── services/
│   ├── api.ts
│   └── websocket.ts
├── types/
│   ├── events.ts
│   ├── roadSegments.ts
│   ├── incidents.ts
│   └── buses.ts
├── data/
│   ├── mockEvents.ts
│   ├── mockRoadSegments.ts
│   ├── mockIncidents.ts
│   └── mockBuses.ts
├── utils/
│   ├── coordinates.ts
│   ├── roadColor.ts
│   └── formatters.ts
├── config/
│   └── maps.ts
├── App.tsx
└── main.tsx
```
Do not create unnecessary files or folders. Keep components small and focused.

## 8. Frontend data contracts
### Event
```ts
export interface Event {
  event_id: string;
  bus_id: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  road_segment_id: string;
  event_type: "road_defect" | "waterlogging" | "traffic" | "incident";
  class_name?: string;
  confidence: number;
  severity?: number;
  frame_id?: number;
  evidence_uri?: string;
}
```

### Road segment
```ts
export interface RoadSegment {
  segment_id: string;
  name?: string;
  geometry: [number, number][]; // GeoJSON order: [lng, lat]
  condition_score: number;
  confidence: number;
  pothole_count: number;
  waterlogging_count: number;
  observation_count: number;
  last_updated: string;
}
```

### Bus
```ts
export interface Bus {
  bus_id: string;
  latitude: number;
  longitude: number;
  heading_deg?: number;
  timestamp: string;
}
```

Keep mock data strictly typed against these interfaces. The UI must not care whether data is mock or live.

## 9. Coordinate rules
Canonical data formats:
- GeoJSON / deck.gl: `[lng, lat]`
- Google Maps: `{lat, lng}`

Never manually flip coordinates in multiple components.

Use one helper:
```ts
export function geoJsonToGooglePath(coords: [number, number][]) {
  return coords.map(([lng, lat]) => ({ lat, lng }));
}
```

## 10. Road-health visualization
Frontend receives `condition_score` from backend and only maps it to a display color.

Display:
- Green = Good
- Yellow = Moderate
- Orange = Poor
- Red = Critical

Do NOT implement or duplicate the backend's scoring/aggregation algorithm in React.

Suggested display mapping:
```ts
if (score >= 80) green;
else if (score >= 60) yellow;
else if (score >= 40) orange;
else red;
```
These are UI thresholds only, not a validated scientific scoring model.

## 11. Map rules
Use:
- `@vis.gl/react-google-maps`
- Google Maps JavaScript API
- Vector map
- configured Map ID
- Advanced Marker Element

Initial center: Chandigarh.

P0 map layers:
1. road-segment polylines
2. defect/event markers
3. bus markers

Do not implement deck.gl during the first map milestone.

## 12. Heatmap rules
Do NOT use Google's deprecated/decommissioned HeatmapLayer.
Use deck.gl later for traffic-density visualization.

deck.gl integration must be isolated in a dedicated component and use the map instance lifecycle correctly (useMap + useEffect; attach/detach overlay once as appropriate).

## 13. API architecture
Initial state should load through REST. WebSocket is for incremental live updates.

Target endpoints:
```text
GET /api/v1/segments/geojson
GET /api/v1/segments/{segment_id}
GET /api/v1/segments/{segment_id}/history
GET /api/v1/events
GET /api/v1/events/{event_id}
GET /api/v1/incidents
GET /api/v1/incidents/{incident_id}
GET /api/v1/buses
WS  /ws/live
```

Do not scatter axios/fetch calls inside UI components. Use `services/api.ts` and `services/websocket.ts`.

## 14. Mock/live architecture
`VITE_USE_MOCK=true` must allow the complete dashboard to run without the backend.

Data flow:
```text
Mock or REST/WebSocket
        ↓
Data/API layer
        ↓
Typed frontend state
        ↓
Map / Analytics / Inspectors
```

Switching mock -> live should not require rewriting UI components.

Mock data should be realistic enough to test:
- good/moderate/poor/critical roads
- multiple events
- repeated observations
- multiple buses
- different confidence/severity
- incidents
- empty/no-event areas

## 15. State separation
Keep these conceptually separate:
- **Backend Data State:** roads, events, incidents, buses, history
- **Map State:** viewport, layers, selected/hovered map item
- **Inspection UI State:** selected road, selected event, selected incident, open/closed drawer
- **Filter State:** event/layer/date/severity/confidence/bus filters

Do not couple WebSocket bus updates to static road-layer rendering unnecessarily.

## 16. Dashboard layout
Map-first command-and-control UI:
```text
Header
├── filters/sidebar
├── main Google Map
├── KPI cards
└── inspector drawer/panel
```

Inspector examples:

Road:
- segment ID/name
- condition score
- confidence
- pothole count
- waterlogging count
- observation count
- last updated
- historical chart

Event:
- type/class
- severity
- confidence
- timestamp
- road segment
- bus ID
- evidence

Incident:
- incident type
- incident score
- vehicle track ID
- plate text if available
- plate confidence
- timestamp/location
- evidence clip

Never present OCR plate text as guaranteed truth; show confidence.

## 17. Performance rules
Assume event volume can grow significantly.
- Use stable IDs for React keys (`event_id`, `segment_id`, `incident_id`, `bus_id`).
- Do not use array index as key for dynamic data.
- Cluster dense event markers when needed.
- Use efficient/batched layers for dense map data.
- Keep bus updates separate from static road data.
- Avoid recreating map overlays every render.
- Avoid huge API payloads; use filtering/time ranges when backend supports them.

## 18. Time/date rules
Use ISO 8601 timestamps with timezone information in API/mock data, e.g.:
`2026-08-29T18:42:11+05:30`

Format timestamps only for display.

## 19. Evidence rules
Prefer evidence references/HTTPS URLs over Base64 media in event JSON.
Frontend should display evidence only when a usable URL/reference is provided.

## 20. Coding style / token efficiency
**Primary instruction: keep code concise and maintainable.**

- Prefer small reusable helpers/components over repetition.
- Do not generate long boilerplate when a short implementation is equivalent.
- Do not duplicate constants/types.
- Do not add abstractions before they are needed.
- Do not create wrapper components with no real value.
- Reuse existing utilities/components instead of rewriting them.
- Do not add comments that merely restate code.
- Add comments only for non-obvious architectural or algorithmic reasons.
- Avoid overly elaborate error-handling frameworks for simple local prototype code.
- Use TypeScript types instead of verbose runtime duplication where reasonable.
- Keep each file focused and reasonably short.
- Prefer configuration/constants over repeated magic strings.
- Before writing a new helper, search the project for an existing equivalent.

## 21. Agent behavior
Before changing code:
1. Inspect the existing files relevant to the requested task.
2. Reuse existing implementation where possible.
3. Make the smallest change that satisfies the requirement.
4. Do not rewrite working files wholesale.
5. Do not add libraries unless the task actually needs them.
6. Do not invent backend fields/endpoints without documenting the change.
7. Do not silently change the architecture.
8. Keep the app runnable after each major change.
9. Run build/type/lint checks after meaningful changes.

When a requested feature is already implemented, do not recreate it.

## 22. Implementation order
Do this in order:

1. Project structure + types + config
2. Google Maps loads with Map ID
3. One Advanced Marker
4. One road polyline
5. Coordinate utility
6. Mock road segments + colored polylines
7. Mock events + event markers
8. Event inspector
9. Dashboard shell/layout
10. Road inspector + historical chart
11. Filters
12. KPI cards
13. Traffic statistics/charts
14. Mock buses
15. REST API service
16. Backend integration
17. WebSocket live updates
18. deck.gl heatmap
19. trip replay / advanced analytics

Do not jump ahead unless necessary.

## 23. First milestone / acceptance test
The first meaningful milestone is:
```text
mock data
  ↓
Google Map
  ↓
Chandigarh
  ↓
1 road polyline
  ↓
1 event marker
  ↓
click road → road details
  ↓
click event → event details
```

Then expand to the full P0 dashboard.

## 24. What not to do
- Do not build a chatbot.
- Do not train an LLM.
- Do not implement AI inference in React.
- Do not calculate city/segment road truth in React.
- Do not make speed mandatory.
- Do not use deprecated Google HeatmapLayer.
- Do not upload/display continuous raw video as the normal data flow.
- Do not make WebSocket the only source of initial state.
- Do not create huge one-file React components.
- Do not over-engineer the prototype.
- Do not implement P1/P2 before P0 works.

## 25. Demo target
The eventual end-to-end story is:
route replay -> AI detects pothole -> metadata/evidence arrives -> correct road segment changes on map -> repeat observation raises confidence -> traffic mode shows vehicle analytics -> incident shows evidence/plate confidence -> road history shows change over time -> city-level map shows actionable priorities.

For Eshan, the critical deliverable is the reliable visualization layer that makes this pipeline understandable to an authority user.

## 26. Source-of-truth rule
The full team document remains the authoritative specification for project-wide architecture, ML, hardware, backend and roadmap. This file is the compact frontend agent context. When a conflict exists, preserve the newest explicit team decision and ask only if implementation cannot proceed without clarification.
