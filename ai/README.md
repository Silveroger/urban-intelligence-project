# SIH 26124 — AI Perception & Edge Subsystem

## Overview
This subsystem executes onboard computer vision analysis for city buses equipped with dashcams and GPS receivers. It conforms strictly to [`docs/AI_CONTRACT.md`](../docs/AI_CONTRACT.md).

## Capabilities
1. **Road Defect & Hazard Detection**:
   - Potholes, surface cracks, damaged pavement, waterlogging / submerged lanes.
2. **Infrastructure Verification**:
   - Missing road dividers, missing zebra crossings, damaged/missing traffic signs.
3. **Traffic Analytics**:
   - Multi-class vehicle classification (`car`, `bus`, `truck`, `motorcycle`, `auto_rickshaw`), vehicle counting, density index estimation, and bottleneck identification.
4. **Pedestrian Safety**:
   - Detection of vulnerable pedestrians and school children crossing in active roadways.
5. **Incident & Offending Vehicle Tracking**:
   - Multi-object tracking (SORT/ByteTrack), rash driving / erratic weaving detection, license plate localization and OCR with confidence scores.
6. **Bandwidth Optimization**:
   - 95% reduction in edge bandwidth by transmitting structured JSON observation events + cropped bounding box keyframes rather than raw video streams.

## Directory Layout
```text
ai/
├── configs/                  # Detection thresholds and class configurations
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
├── test_video_generator.py          # Synthetic test video + GPS track generator
└── README.md
```

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
