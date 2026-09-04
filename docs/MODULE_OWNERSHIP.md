# Module Ownership & Team Boundaries

## 1. Ownership Roster

| Subsystem / Area | Lead Owner | Primary Repository Paths | Core Responsibilities |
|---|---|---|---|
| **GIS Frontend / Dashboard** | **Eshan** | `src/` | Map rendering, road condition styling, Advanced Markers, deck.gl overlays, filter panel, KPI cards, Video Hub, GPS Pipeline drawer, inspector drawers, UI state management. |
| **Backend & Geospatial Ingestion** | **Butar** | `backend/` | FastAPI services, PostGIS/Shapely spatial indexing, GPS map-matching, multi-pass score aggregation, video processing background worker, REST/WebSocket API endpoints. |
| **Road AI & Defect Detectors** | **Chirag** | `ai/detectors/road_defect_detector.py`, `ai/detectors/infrastructure_detector.py` | Pothole detection, crack segmentation, infrastructure deficit reasoning, defect severity scoring, road dataset curation. |
| **Traffic, Pedestrian & Incident AI**| **Jasleen** | `ai/tracker/`, `ai/detectors/traffic_density_detector.py`, `ai/detectors/pedestrian_detector.py`, `ai/detectors/plate_recognizer.py` | Vehicle tracking, traffic density estimation, pedestrian crossing risk detection, illegal parking detection, license plate OCR. |
| **Hardware & Vehicle Sensing** | **Manveer** | `ai/telemetry/`, `ai/test_video_generator.py` | Camera mounts, GPS receiver integration, NMEA parsing, vehicle power management, edge sensor synchronization. |
| **Edge Compute & Database** | **Navneet** | `ai/edge_optimizer.py`, `run_live_scanner.py`, `supabase/` | ONNX/TensorRT edge optimization, desktop live scanner HUD, Supabase migrations, RLS policies, Realtime publication. |

---

## 2. Boundary & Collaboration Rules
1. **Clear Module Ownership:** Team members possess authoritative ownership over their designated subsystems.
2. **Interface Contracts First:** Cross-boundary changes (modifying API endpoints, changing event schemas, altering coordinate formats) require updating [API_CONTRACT.md](API_CONTRACT.md) or [AI_CONTRACT.md](AI_CONTRACT.md) in agreement with affected subsystem owners before altering implementation code.
3. **No Uncoordinated Subsystem Rewrites:** Code within another subsystem's directory must not be rewritten without coordination.
