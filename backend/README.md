# SIH 26124 — Centralized Backend & Spatial Processing Subsystem

## Overview
This subsystem provides the high-performance FastAPI service, spatial road-matching, multi-pass observation scoring, and real-time WebSocket distribution for the Urban Intelligence Platform.

## Features
- **Spatial Map-Matching**: Projects discrete GPS detections to road segment centerlines.
- **Dynamic Condition Scoring**: Real-time road health degradation & confidence estimation ($0-100$).
- **REST Endpoints**: Conforms to [`docs/API_CONTRACT.md`](../docs/API_CONTRACT.md).
- **WebSocket Protocol**: Real-time updates via `/ws/live` (`BUS_TELEMETRY`, `NEW_EVENT`, `NEW_INCIDENT`, `SEGMENT_UPDATE`).
- **Edge Ingestion**: Accepts edge telemetry, structured perception observations, and automated batch video processing jobs.

## Running the Backend Server
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger Documentation will be available at: `http://localhost:8000/docs`.
