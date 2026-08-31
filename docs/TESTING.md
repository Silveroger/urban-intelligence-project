# Testing Strategy & Procedures

## 1. Testing Strategy Overview
Quality assurance is enforced across four distinct layers to ensure UI reliability, strict contract adherence, and spatial precision:

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
│  Layer 4: End-to-End Build & Visual Verification       │
└────────────────────────────────────────────────────────┘
```

---

## 2. Verification Commands

Run these checks before committing code changes:

| Target | Command | Purpose |
|---|---|---|
| **Linter** | `npm run lint` | Verifies code styling, unused variables, and React hook dependency rules. |
| **Typecheck & Build** | `npm run build` | Executes `tsc -b` (project reference build) followed by `vite build` to ensure zero compilation or type errors. |
| **Development Preview** | `npm run preview` | Spins up a local production build server for realistic performance testing. |

---

## 3. Specialized Testing Procedures

### 3.1 GIS & Coordinate Transformations
- **Coordinate Order:** Verify that coordinate array inputs `[lng, lat]` are converted into `{lat, lng}` objects via `geoJsonToGooglePath` without reversing lat/lng axes.
- **Polyline Integrity:** Verify that road polylines render over actual street corridors without disjointed vertices.
- **Marker Anchors:** Ensure Advanced Marker pins correctly anchor at exact coordinate centroids.

### 3.2 Contract & Fixture Validation
- **Interface Alignment:** Verify that all mock data files in `src/data/` strictly type-check against domain interfaces in `src/types/` (`RoadSegment`, `Event`, `Incident`, `Bus`).
- **Null Safety:** Verify that optional fields (`heading_deg`, `evidence_uri`, `plate_text`) do not cause `TypeError` crashes when null or undefined.

### 3.3 Live & Mock Mode Integration
- **Mock Fallback:** Ensure `VITE_USE_MOCK=true` renders all map layers, cards, and charts without network errors.
- **Live Resilience:** Ensure graceful handling (loading skeletons and error alerts) if `VITE_USE_MOCK=false` is set and the backend endpoint is temporarily unreachable.

---

## 4. Definition of Done
A feature or bugfix is complete only after:
1. `npm run lint` passes with zero errors.
2. `npm run build` compiles with zero TypeScript errors.
3. Relevant interactive workflows (clicking segments, toggling filters, opening inspectors) are verified in the browser.
4. Documentation and contracts are updated if interfaces changed.
