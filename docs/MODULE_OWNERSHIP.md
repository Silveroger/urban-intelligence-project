# Module Ownership & Team Boundaries

## 1. Ownership Roster

| Subsystem / Area | Lead Owner | Primary Repository Paths | Core Responsibilities |
|---|---|---|---|
| **GIS Frontend / Dashboard** | **Eshan** | `src/`, `public/` | Map rendering, road condition styling, Advanced Markers, deck.gl overlays, filter panel, KPI cards, inspector drawers, UI state management. |
| **Backend & Geospatial Ingestion** | **Aryush Butar** | `backend/` | FastAPI services, PostGIS spatial indexing, GPS map-matching, multi-pass score aggregation, REST/WebSocket API endpoints, Supabase Storage. |
| **Road AI & Defect Dataset** | **Chirag** | `ai/road/` | Pothole detection, crack segmentation, defect severity scoring, road dataset curation and annotation. |
| **Traffic & Incident AI** | **Jasleen** | `ai/traffic/`, `ai/incident/` | Vehicle detection & tracking, traffic flow estimation, illegal parking detection, license plate OCR. |
| **Hardware & Vehicle Sensing** | **Manveer** | `edge/hardware/` | Camera mounts, GPS receiver integration, vehicle power management, edge sensor synchronization. |
| **Edge Compute & Integration** | **Navneet** | `edge/integration/` | Frame sampling, on-bus inference packaging, telemetry upload pipelines, edge-to-backend networking. |

---

## 2. Boundary & Collaboration Rules
1. **Clear Module Ownership:** Team members possess authoritative ownership over their designated subsystems.
2. **Interface Contracts First:** Cross-boundary changes (modifying API endpoints, changing event schemas, altering coordinate formats) require updating [`docs/API_CONTRACT.md`](API_CONTRACT.md) or [`docs/AI_CONTRACT.md`](AI_CONTRACT.md) in agreement with affected subsystem owners before altering implementation code.
3. **No Uncoordinated Subsystem Rewrites:** Code within another subsystem's directory must not be casually rewritten without coordination.
4. **Defect & Discrepancy Tracking:** All cross-cutting bugs, contract discrepancies, and integration gaps must be tracked in [`docs/BUGS_AND_DISCREPANCIES.md`](BUGS_AND_DISCREPANCIES.md).
