# Testing Strategy & Procedures

## 1. Testing Strategy Overview
Quality assurance is enforced across five distinct layers to ensure UI reliability, strict contract adherence, backend spatial precision, and edge AI execution:

```text
┌────────────────────────────────────────────────────────┐
│  Layer 1: Static Analysis (ESLint & Strict TypeScript) │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│  Layer 2: Spatial & Coordinate Unit Verification       │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│  Layer 3: Contract & Fixture Shape Validation          │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│  Layer 4: Backend REST & WebSocket Server Verification │
└───────────────────────────┬────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│  Layer 5: Edge AI Perception & Desktop Scanner Run     │
└────────────────────────────────────────────────────────┘
```

---

## 2. Verification Commands

Run these checks before committing code changes:

| Target | Command | Purpose |
|---|---|---|
| **Frontend Linter** | `npm run lint` | Verifies code styling, unused variables, and React hook dependency rules. |
| **Frontend Typecheck & Build** | `npm run build` | Executes `tsc -b` followed by `vite build` to ensure zero compilation or type errors. |
| **Backend Application Server** | `python -m uvicorn backend.app.main:app` | Validates FastAPI routes, Pydantic models, and WebSocket hub startup. |
| **Edge AI Perception Scanner** | `python run_live_scanner.py --no-window` | Runs headless end-to-end edge pipeline test across synthetic bus run. |
| **Supabase Cloud Verification** | `node scripts/verify_supabase.cjs` | Validates database connectivity, tables, and RLS policies. |

---

## 3. Specialized Testing Procedures

### 3.1 GIS & Coordinate Transformations
- **Coordinate Order:** Verify that coordinate array inputs `[lng, lat]` are converted into `{lat, lng}` objects via `geoJsonToGooglePath` without reversing lat/lng axes.
- **Polyline Integrity:** Verify that road polylines render over actual street corridors without disjointed vertices.
- **Marker Anchors:** Ensure Advanced Marker pins correctly anchor at exact coordinate centroids.

### 3.2 Contract & Fixture Validation
- **Interface Alignment:** Verify that all mock data files in `src/data/` strictly type-check against domain interfaces in `src/types/` (`RoadSegment`, `Event`, `Incident`, `Bus`, `GpsRecord`).
- **Null Safety:** Verify that optional fields (`heading_deg`, `evidence_uri`, `plate_text`, `bbox`) do not cause `TypeError` crashes when null or undefined.

### 3.3 Live & Mock Mode Integration
- **Mock Fallback:** Ensure `VITE_USE_MOCK=true` renders all map layers, cards, and charts without network errors.
- **Live Resilience:** Ensure graceful handling (loading skeletons and error alerts) if `VITE_USE_MOCK=false` is set and the backend endpoint is temporarily unreachable.

### 3.4 Video Processing & Detector Toggles
- Ensure `/api/v1/ingest/video/process` handles missing GPS tracks gracefully using default camera centroids.
- Test detector flags JSON parsing with individual modules enabled/disabled.

---

## 4. Definition of Done
A feature or bugfix is complete only after:
1. `npm run lint` passes with zero errors.
2. `npm run build` compiles with zero TypeScript errors.
3. Relevant interactive workflows (clicking segments, toggling filters, opening inspectors, triggering video scans) are verified in the browser.
4. Documentation and contracts in `docs/` are updated if interfaces changed.
