# Agent & Implementation State

> **Note:** This document tracks temporary, current development state. Stale entries are pruned upon milestone completion.

## 1. Current Implementation Baseline
- **Frontend Dashboard:** P0 MVP complete (Google Maps vector rendering, colored road polylines, Advanced Markers for defect/incident events, bus markers, filter sidebar, KPI cards, segment/event/incident inspector drawers, historical degradation charts).
- **Heatmap Layer:** Phase 1 deck.gl GPU heatmap overlay implemented and functional via `@deck.gl/google-maps`.
- **Data Mode:** Standalone mock data mode operational (`VITE_USE_MOCK=true`) in `src/services/api.ts`.
- **Type Safety & Build:** Strict TypeScript validation enabled; clean ESLint status; zero compiler errors.

---

## 2. Active Milestones & Focus
- **Current Milestone:** Backend REST & WebSocket integration with PostGIS ingestion services.
- **Active Tasks:**
  - Synchronize live backend REST schemas with [API_CONTRACT.md](file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/API_CONTRACT.md).
  - Implement live WebSocket reconnect logic in `src/services/websocket.ts`.
  - Validate live GPS stream updates for multiple moving fleet buses.

---

## 3. Known Blockers & Dependencies
- **Live Backend Availability:** Backend PostGIS instance currently in parallel development (Butar). Frontend continues using typed mock fixtures.
- **Google Maps API Key:** Ensure valid Vector Map ID is configured in `.env` for hardware-accelerated 3D vector map features.

---

## 4. Architectural Decision References
- All architectural decisions are formally documented in [DECISIONS.md](file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/DECISIONS.md).
