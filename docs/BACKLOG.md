# Project Backlog & Planned Work

## 1. P0 — Immediate Integration Tasks
- [ ] **REST API Live Data Sync:** Connect `src/services/api.ts` to live FastAPI endpoints (`/api/v1/segments/geojson`, `/api/v1/events`, `/api/v1/incidents`, `/api/v1/buses`).
- [ ] **WebSocket Real-Time Consumer:** Connect `src/services/websocket.ts` to `/ws/live` for real-time bus telemetry updates and instant event markers.
- [ ] **Contract Fixture Validation:** Add automated contract validation tests to verify API payload shapes against TypeScript interfaces.
- [ ] **Live Error Handling:** Add toast notifications and retry mechanisms for network failures and WebSocket reconnects.

---

## 2. P1 — Advanced Dashboard Features
- [ ] **Trip Replay & Time Scrubber:** Add interactive time slider to scrub through historical bus runs and observe defect progression over 24-hour / 7-day windows.
- [ ] **Evidence Media Inspection Modal:** Add high-resolution image viewer with zoom/pan capabilities for pothole crops and defect bounding boxes.
- [ ] **Maintenance Priority Ranking Tool:** Build a dedicated view sorting city segments by defect density, condition degradation rate, and traffic load.
- [ ] **Work-Order Export:** Implement PDF/CSV/GeoJSON export of repair work orders with GPS coordinates and evidence links.
- [ ] **Fleet Sensing Coverage Analytics:** Add coverage heatmap showing city road segments traversed by buses in the last 24/48 hours.

---

## 3. P2 — Future Extensions
- [ ] **Missing Infrastructure Reasoning:** Map visualization for missing zebra crossings, faded lane markings, and damaged road signage.
- [ ] **Route Delay & Congestion Analysis:** Correlate road defects with bus schedule deviations and transit corridor travel times.
- [ ] **Origin-Destination Flow Modeling:** Visualize aggregated commuter flow matrices across municipal sectors.
