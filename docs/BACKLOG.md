# Project Backlog & Planned Work

## 1. P0 — Immediate Integration Tasks (Completed Baseline)
- [x] **REST API Live Data Sync:** Connect `src/services/api.ts` to live FastAPI endpoints (`/api/v1/segments/geojson`, `/api/v1/events`, `/api/v1/incidents`, `/api/v1/buses`, `/api/v1/analytics/summary`).
- [x] **WebSocket Real-Time Consumer:** Connect `src/services/websocket.ts` to `/ws/live` for real-time bus telemetry updates and instant event markers.
- [x] **Supabase Telemetry Ingestion & Realtime Channel:** Implemented migrations (`supabase/migrations/`) and frontend streaming client (`src/services/supabase.ts`, `src/services/gpsPipeline.ts`).
- [x] **Edge AI Video Ingestion Hub:** Ingestion modal (`src/components/VideoHub/VideoIngestModal.tsx`) with video file & GPS track upload and selective detector flags.
- [x] **Modular Computer Vision Pipeline:** 5 specialized detector modules (Road defects, waterlogging, traffic density, pedestrian safety, vehicle tracking & OCR).
- [x] **Live Desktop Scanner HUD:** Interactive desktop popup window (`run_live_scanner.py`) with telemetry overlays and bounding boxes.

---

## 2. P1 — Advanced Dashboard Features & Operations
- [ ] **Maintenance Priority Ranking View:** Build a dedicated view sorting city segments by defect density, condition degradation rate, and traffic load.
- [ ] **Work-Order Export:** Implement PDF/CSV/GeoJSON export of repair work orders with GPS coordinates and evidence links.
- [ ] **Trip Replay & Time Scrubber:** Add interactive time slider to scrub through historical bus runs and observe defect progression over 24-hour / 7-day windows.
- [ ] **Field Hardware Multi-Bus Deployment:** Connect physical dashcam streams (RTSP / USB) and NMEA GPS receivers from pilot test fleet.
- [ ] **Fleet Sensing Coverage Analytics:** Add coverage heatmap showing city road segments traversed by buses in the last 24/48 hours.

---

## 3. P2 — Future Extensions
- [ ] **Advanced Infrastructure Reasoning:** City-wide automated auditing of missing zebra crossings, faded lane markings, and damaged road signage.
- [ ] **Route Delay & Congestion Analysis:** Correlate road defects with bus schedule deviations and transit corridor travel times.
- [ ] **Origin-Destination Flow Modeling:** Visualize aggregated commuter flow matrices across municipal sectors.
