# Testing Strategy & Procedures

## 1. Testing Strategy Overview
Quality assurance is enforced across five distinct layers to ensure UI reliability, strict contract adherence, backend calculation correctness, and spatial precision:

```text
┌────────────────────────────────────────────────────────┐
│  Layer 1: Frontend Static Analysis & Build             │
│  (ESLint, Strict TypeScript, tsc -b, Vite build)       │
├────────────────────────────────────────────────────────┤
│  Layer 2: Backend Unit & Contract Tests                │
│  (pytest, Scoring Formula, Severity, Validation)       │
├────────────────────────────────────────────────────────┤
│  Layer 3: Spatial & Coordinate Verification            │
│  (GeoJSON [lng, lat] vs Google {lat, lng}, PostGIS)    │
├────────────────────────────────────────────────────────┤
│  Layer 4: Diagnostic Connectivity & Ingestion Scripts  │
│  (test_connection.py, test_ingestion.py)               │
├────────────────────────────────────────────────────────┤
│  Layer 5: End-to-End Integration & Visual Verification │
│  (Live Dashboard, Inspector Drawers, WebSocket)        │
└────────────────────────────────────────────────────────┘
```

---

## 2. Verification Commands

### 2.1 Frontend Checks (from project root)

| Target | Command | Purpose |
|---|---|---|
| **Linter** | `npm run lint` | Verifies code styling, unused variables, and React hook dependency rules. |
| **Typecheck & Build** | `npm run build` | Executes `tsc -b` (project reference build) followed by `vite build` to ensure zero compilation or type errors. |
| **Development Preview** | `npm run preview` | Spins up a local production build server for realistic performance testing. |

### 2.2 Backend Checks (from `backend/` directory)

| Target | Command | Purpose |
|---|---|---|
| **Full Test Suite** | `pytest` | Runs all unit, route, and validation tests in `tests/`. |
| **Scoring Formula Test** | `pytest tests/test_scoring.py` | Verifies deterministic health scoring penalties and repeat multipliers. |
| **Coordinates Test** | `pytest tests/test_coordinates.py` | Validates latitude/longitude bounding boxes and GeoJSON transformations. |
| **API Route Tests** | `pytest tests/test_api_routes.py` | Tests REST endpoints with mock database sessions. |
| **WebSocket Test** | `pytest tests/test_websocket.py` | Tests WebSocket connection manager and frame broadcast logic. |
| **Database Diagnostics** | `python scripts/test_connection.py` | Verifies PostGIS version, schema installation, and table accessibility. |
| **End-to-End Ingestion** | `python scripts/test_ingestion.py` | Simulates live edge observation upload, map matching, and score update. |

---

## 3. Specialized Testing Procedures

### 3.1 GIS & Coordinate Transformations
- **Coordinate Order:** Verify that coordinate array inputs `[lng, lat]` are converted into `{lat, lng}` objects via `geoJsonToGooglePath` without reversing lat/lng axes.
- **Polyline Integrity:** Verify that road polylines render over actual street corridors without disjointed vertices.
- **Marker Anchors:** Ensure Advanced Marker pins correctly anchor at exact coordinate centroids.

### 3.2 Contract & Fixture Validation
- **Interface Alignment:** Verify that all mock data files in `src/data/` strictly type-check against domain interfaces in `src/types/` (`RoadSegment`, `Event`, `Incident`, `Bus`).
- **Null Safety:** Verify that optional fields (`heading_deg`, `evidence_uri`, `plate_text`) do not cause `TypeError` crashes when null or undefined.
- **Defect Tracking:** Refer to [`docs/BUGS_AND_DISCREPANCIES.md`](BUGS_AND_DISCREPANCIES.md) for known edge cases and ongoing interface alignments.

### 3.3 Live & Mock Mode Integration
- **Mock Fallback:** Ensure `VITE_USE_MOCK=true` renders all map layers, cards, and charts without network errors.
- **Live Resilience:** Ensure graceful handling (loading skeletons and error alerts) if `VITE_USE_MOCK=false` is set and the backend endpoint is temporarily unreachable.

---

## 4. Definition of Done
A feature or bugfix is complete only after:
1. `npm run lint` passes with zero errors.
2. `npm run build` compiles with zero TypeScript errors.
3. Backend tests pass (`pytest` exits with code 0).
4. Relevant interactive workflows (clicking segments, toggling filters, opening inspectors) are verified in the browser.
5. Documentation and contracts are updated if interfaces changed.
