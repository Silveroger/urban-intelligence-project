# SIH 26124 — AI Perception & Edge Subsystem

## Overview
This subsystem executes onboard computer vision analysis and hardware telemetry reception for city buses equipped with dashcams, GPS receivers, and sensor modules.

All detector algorithms and models developed on Chirag's branch have been **strictly preserved rather than rewritten**. Inference outputs are translated to canonical schemas via `BackendIngestAdapter` and dispatched directly to the canonical FastAPI Backend (`POST /api/v1/telemetry`, `POST /api/v1/observations`, `POST /api/v1/incidents`).

---

## Capabilities
1. **Road Defect & Hazard Detection**:
   - Potholes, surface cracks, damaged pavement, waterlogging / submerged lanes.
   - Computes civil engineering diagnostics (`risk_score`, `breadth_cm`, `depth_cm`, `dimensions`, `risk_assessment`) stored in PostgreSQL `observations.metadata` JSONB.
2. **Infrastructure Verification**:
   - Missing road dividers, missing zebra crossings, damaged/missing traffic signs.
3. **Traffic Analytics**:
   - Multi-class vehicle classification (`car`, `bus`, `truck`, `motorcycle`, `auto_rickshaw`), vehicle counting, density index estimation, and bottleneck identification.
4. **Pedestrian Safety**:
   - Detection of vulnerable pedestrians and school children crossing in active roadways (normalized to canonical incidents with `class_name="vulnerable_pedestrian"`).
5. **Incident & Offending Vehicle Tracking**:
   - Multi-object tracking (SORT/ByteTrack), rash driving / erratic weaving detection, license plate localization and OCR with confidence scores.
6. **Bandwidth Optimization**:
   - 95% reduction in edge bandwidth by transmitting structured JSON observation events + cropped bounding box keyframes rather than raw video streams.

---

## Directory Layout
```text
ai/
├── adapter/
│   └── backend_adapter.py           # Thin boundary adapter (BackendIngestAdapter)
├── configs/
│   └── config.py                    # Detection thresholds and class configurations
├── detectors/
│   ├── road_defect_detector.py      # Potholes, damaged roads, waterlogging
│   ├── infrastructure_detector.py   # Missing dividers, zebra crossings, signboards
│   ├── traffic_density_detector.py  # Vehicle classification & counting
│   ├── pedestrian_detector.py       # Vulnerable pedestrians & school children
│   └── plate_recognizer.py          # License plate OCR & confidence
├── tracker/
│   └── vehicle_tracker.py           # Multi-object tracking & rash driving detector
├── telemetry/
│   └── gps_sync.py                  # Frame-to-GPS/timestamp interpolation
├── pipeline.py                      # Master Edge AI pipeline
├── edge_optimizer.py                # Bandwidth optimizer & evidence packaging
├── hardware_receiver.py             # UDP telemetry listener for ESP32/GPS
├── test_video_generator.py          # Synthetic test video + GPS track generator
├── sample_bus_camera.mp4            # Sample dashcam video for testing
├── sample_gps_track.json            # Sample synchronized GPS track
├── requirements.txt                 # AI-specific pinned dependencies
└── README.md
```

---

## Running the Pipeline

### 1. Generating a Test Video & GPS Track
```bash
python -m ai.test_video_generator
```

### 2. Processing a Video File
```bash
python -m ai.pipeline ai/sample_bus_camera.mp4 ai/sample_gps_track.json
```

### 3. Live Edge Scanner Streaming to Backend
Stream real-time observations and telemetry directly into the canonical backend:
```bash
python run_live_scanner.py --post-backend
```

### 4. Hardware UDP Telemetry & AI Receiver
Receive live ESP32/GPS and edge camera feeds and dispatch normalized events to the backend:
```bash
python run_hardware_receiver.py --backend http://localhost:8000
```
