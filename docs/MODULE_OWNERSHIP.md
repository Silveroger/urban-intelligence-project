# Module Ownership & Team Boundaries

## 1. Ownership Roster

| Subsystem / Area | Lead Owner | Primary Repository Paths | Core Responsibilities |
|---|---|---|---|
| **GIS Frontend / Dashboard** | **Eshan** | `urban-dashboard/src/` | Map rendering, road condition styling, Advanced Markers, deck.gl overlays, filter panel, KPI cards, inspector drawers, UI state management. |
| **Backend & Geospatial Ingestion** | **Butar** | `backend/` | FastAPI services, PostGIS spatial indexing, GPS map-matching, multi-pass score aggregation, REST/WebSocket API endpoints. |
| **Road AI & Defect Dataset** | **Chirag** | `ai/road/` | Pothole detection, crack segmentation, defect severity scoring, road dataset curation and annotation. |
| **Traffic & Incident AI** | **Jasleen** | `ai/traffic/`, `ai/incident/` | Vehicle detection & tracking, traffic flow estimation, illegal parking detection, license plate OCR. |
| **Hardware & Vehicle Sensing** | **Manveer** | `edge/hardware/` | Camera mounts, GPS receiver integration, vehicle power management, edge sensor synchronization. |
| **Edge Compute & Integration** | **Navneet** | `edge/integration/` | Frame sampling, on-bus inference packaging, telemetry upload pipelines, edge-to-backend networking. |

---

## 2. Boundary & Collaboration Rules
1. **Clear Module Ownership:** Team members possess authoritative ownership over their designated subsystems.
2. **Interface Contracts First:** Cross-boundary changes (modifying API endpoints, changing event schemas, altering coordinate formats) require updating [API_CONTRACT.md](file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/API_CONTRACT.md) or [AI_CONTRACT.md](file:///c:/Users/Eshan%20Sharma/Desktop/sih%20project/urban-dashboard/docs/AI_CONTRACT.md) in agreement with affected subsystem owners before altering implementation code.
3. **No Uncoordinated Subsystem Rewrites:** Code within another subsystem's directory must not be casually rewritten without coordination.
