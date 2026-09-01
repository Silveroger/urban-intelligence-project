"""
SIH 26124 — Edge Ingestion & Video Pipeline Trigger Endpoints
Conforms to docs/AI_CONTRACT.md, docs/API_CONTRACT.md, and docs/ARCHITECTURE.md.
"""

import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import Dict, Optional
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.models.event import ObservationEvent
from backend.app.models.incident import Incident
from backend.app.models.telemetry import BusTelemetry
from backend.app.services.aggregation import obs_store
from backend.app.services.spatial_engine import spatial_engine
from backend.app.services.websocket_hub import ws_hub

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/observation")
async def ingest_observation(event: ObservationEvent):
    """
    Ingests structured observation from edge bus perception models.
    Recalculates spatial road condition score and broadcasts updates via WebSocket.
    """
    # 1. Update spatial road condition
    updated_feat = spatial_engine.ingest_observation(event)
    
    # 2. Store observation
    event_dict = event.model_dump()
    obs_store.add_event(event_dict)

    # 3. Broadcast to all live dashboard clients
    await ws_hub.broadcast_json({
        "type": "NEW_EVENT",
        "payload": event_dict
    })

    if updated_feat:
        await ws_hub.broadcast_json({
            "type": "SEGMENT_UPDATE",
            "payload": updated_feat
        })

    return {"status": "ok", "event_id": event.event_id, "matched_segment": event.road_segment_id}


@router.post("/telemetry")
async def ingest_telemetry(telemetry: BusTelemetry):
    """
    Ingests real-time bus GPS coordinate and heading ping.
    """
    t_dict = telemetry.model_dump()
    obs_store.update_telemetry(telemetry.bus_id, t_dict)

    # Broadcast bus position delta
    await ws_hub.broadcast_json({
        "type": "BUS_TELEMETRY",
        "payload": t_dict
    })

    return {"status": "ok", "bus_id": telemetry.bus_id}


@router.post("/incident")
async def ingest_incident(incident: Incident):
    """
    Ingests traffic incident / offending vehicle tracking alert.
    """
    inc_dict = incident.model_dump()
    obs_store.add_incident(inc_dict)

    await ws_hub.broadcast_json({
        "type": "NEW_INCIDENT",
        "payload": inc_dict
    })

    return {"status": "ok", "incident_id": incident.incident_id}


# Video Processing Pipeline Execution Endpoint
processing_state = {
    "is_running": False,
    "progress": 0.0,
    "current_frame": 0,
    "total_frames": 0,
    "status_message": "Idle",
    "last_result": None
}


@router.get("/video/status")
async def get_video_processing_status():
    return processing_state


@router.post("/video/process")
async def trigger_video_processing(
    background_tasks: BackgroundTasks,
    bus_id: str = Form(default="BUS-101"),
    use_sample: bool = Form(default=False),
    show_window: bool = Form(default=True),
    enabled_detectors: str = Form(default="{}"),
    video_file: Optional[UploadFile] = File(default=None),
    gps_file: Optional[UploadFile] = File(default=None)
):
    """
    Accepts video and GPS track uploads (or sample video preset), runs OpenCV + YOLO
    edge perception pipeline, displays scanning window if requested, and streams
    live detections to the dashboard.

    enabled_detectors: JSON string mapping category keys to booleans.
        Keys: road_defect, waterlogging, traffic, incident.
        Example: '{"road_defect": true, "waterlogging": false, "traffic": true, "incident": true}'
        If a key is False the corresponding detector is completely skipped.

    Accepted video formats: .mp4 .avi .mkv .mov .h264 .h265 .mjpeg .ts .raw .flv .webm
    (covers all common SBC / camera-module output containers)
    """
    if processing_state["is_running"]:
        raise HTTPException(status_code=409, detail="A video processing pipeline is already running.")

    # Parse detector toggle map
    try:
        det_flags = json.loads(enabled_detectors) if enabled_detectors else {}
    except json.JSONDecodeError:
        det_flags = {}

    upload_dir = settings.STATIC_DIR / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    video_path = None
    gps_path = None

    if use_sample or video_file is None:
        sample_vid = Path("ai/sample_bus_camera.mp4")
        sample_gps = Path("ai/sample_gps_track.json")
        if not sample_vid.exists():
            # Generate sample run if not already present
            from ai.test_video_generator import generate_synthetic_bus_run
            generate_synthetic_bus_run()

        video_path = str(sample_vid)
        gps_path = str(sample_gps) if sample_gps.exists() else None
    else:
        # Save uploaded video
        saved_vid = upload_dir / video_file.filename
        with open(saved_vid, "wb") as buffer:
            shutil.copyfileobj(video_file.file, buffer)
        video_path = str(saved_vid)

        if gps_file:
            saved_gps = upload_dir / gps_file.filename
            with open(saved_gps, "wb") as buffer:
                shutil.copyfileobj(gps_file.file, buffer)
            gps_path = str(saved_gps)

    # Launch processing in background
    background_tasks.add_task(run_pipeline_task, bus_id, video_path, gps_path, show_window, det_flags)

    return {
        "status": "processing_started",
        "bus_id": bus_id,
        "video_path": video_path,
        "gps_path": gps_path,
        "show_window": show_window,
        "enabled_detectors": det_flags
    }


def run_pipeline_task(
    bus_id: str,
    video_path: str,
    gps_path: Optional[str],
    show_window: bool = True,
    enabled_detectors: Optional[Dict] = None
):
    from ai.pipeline import EdgeAIPipeline

    processing_state["is_running"] = True
    processing_state["progress"] = 0.0
    processing_state["status_message"] = "Initializing Edge AI perception..."

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def on_progress(p, cur, tot):
        processing_state["progress"] = round(p * 100, 1)
        processing_state["current_frame"] = cur
        processing_state["total_frames"] = tot
        processing_state["status_message"] = f"Processing frame {cur}/{tot} ({processing_state['progress']}%)"

    def on_event(msg):
        # Ingest into backend store & spatial engine
        payload = msg["payload"]
        if msg["type"] == "NEW_EVENT":
            obs_store.add_event(payload)
            # Match road segment and update score
            evt_obj = ObservationEvent(**payload)
            updated_feat = spatial_engine.ingest_observation(evt_obj)
            loop.run_until_complete(ws_hub.broadcast_json(msg))
            if updated_feat:
                loop.run_until_complete(ws_hub.broadcast_json({
                    "type": "SEGMENT_UPDATE",
                    "payload": updated_feat
                }))
        elif msg["type"] == "NEW_INCIDENT":
            obs_store.add_incident(payload)
            loop.run_until_complete(ws_hub.broadcast_json(msg))

    def on_telemetry(t):
        obs_store.update_telemetry(t["bus_id"], t)
        loop.run_until_complete(ws_hub.broadcast_json({
            "type": "BUS_TELEMETRY",
            "payload": t
        }))

    try:
        pipeline = EdgeAIPipeline(bus_id=bus_id)
        res = pipeline.process_video(
            video_path=video_path,
            gps_path=gps_path,
            show_window=show_window,
            delay_ms=25,
            enabled_detectors=enabled_detectors,
            on_event_callback=on_event,
            on_telemetry_callback=on_telemetry,
            on_progress_callback=on_progress
        )
        processing_state["last_result"] = res
        processing_state["status_message"] = "Processing completed successfully!"
    except Exception as e:
        processing_state["status_message"] = f"Processing error: {str(e)}"
    finally:
        processing_state["is_running"] = False
        loop.close()
