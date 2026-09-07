"""
SIH 26124 — Edge Video Pipeline Trigger Endpoints
Adapts Chirag's video runner into Eshan's canonical PostgreSQL + PostGIS backend.
"""

import asyncio
import json
import logging
import shutil
import sys
from pathlib import Path

# Ensure project root is available on sys.path for ai package
repo_root = Path(__file__).resolve().parent.parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from typing import Dict, Optional
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from app.core.config import settings
from app.db.database import AsyncSessionLocal
from ai.adapter.backend_adapter import BackendIngestAdapter
from app.services.ingestion import ingest_observation
from app.services.telemetry import process_bus_telemetry
from app.services.incidents import create_incident
from app.schemas.observations import ObservationCreate
from app.schemas.telemetry import TelemetryCreate
from app.schemas.incidents import IncidentCreate

logger = logging.getLogger("urban_intel.video_pipeline")

router = APIRouter(tags=["Video Processing Pipeline"])

processing_state = {
    "is_running": False,
    "progress": 0.0,
    "current_frame": 0,
    "total_frames": 0,
    "status_message": "Idle",
    "last_result": None,
}


@router.get("/status")
async def get_video_processing_status():
    """Returns current edge video processing progress and results."""
    return processing_state


@router.post("/process")
async def trigger_video_processing(
    background_tasks: BackgroundTasks,
    bus_id: str = Form(default="BUS-101"),
    use_sample: bool = Form(default=False),
    show_window: bool = Form(default=False),
    enabled_detectors: str = Form(default="{}"),
    video_file: Optional[UploadFile] = File(default=None),
    gps_file: Optional[UploadFile] = File(default=None),
):
    """
    Accepts video and GPS track uploads (or sample video preset), runs OpenCV + YOLO
    edge perception pipeline, and normalizes/ingests observations into canonical PostGIS backend.
    """
    if processing_state["is_running"]:
        raise HTTPException(status_code=409, detail="A video processing pipeline is already running.")

    try:
        det_flags = json.loads(enabled_detectors) if enabled_detectors else {}
    except json.JSONDecodeError:
        det_flags = {}

    upload_dir = Path("backend/static/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    video_path = None
    gps_path = None

    if use_sample or video_file is None:
        sample_vid = Path("ai/sample_bus_camera.mp4")
        sample_gps = Path("ai/sample_gps_track.json")
        if not sample_vid.exists():
            from ai.test_video_generator import generate_synthetic_bus_run
            generate_synthetic_bus_run()

        video_path = str(sample_vid)
        gps_path = str(sample_gps) if sample_gps.exists() else None
    else:
        saved_vid = upload_dir / (video_file.filename or "upload.mp4")
        with open(saved_vid, "wb") as buffer:
            shutil.copyfileobj(video_file.file, buffer)
        video_path = str(saved_vid)

        if gps_file:
            saved_gps = upload_dir / (gps_file.filename or "track.json")
            with open(saved_gps, "wb") as buffer:
                shutil.copyfileobj(gps_file.file, buffer)
            gps_path = str(saved_gps)

    background_tasks.add_task(run_pipeline_task, bus_id, video_path, gps_path, show_window, det_flags)

    return {
        "status": "processing_started",
        "bus_id": bus_id,
        "video_path": video_path,
        "gps_path": gps_path,
        "show_window": show_window,
        "enabled_detectors": det_flags,
    }


def run_pipeline_task(
    bus_id: str,
    video_path: str,
    gps_path: Optional[str],
    show_window: bool = False,
    enabled_detectors: Optional[Dict] = None,
):
    """
    Background worker executing EdgeAIPipeline and normalizing events through
    BackendIngestAdapter into canonical PostgreSQL + PostGIS tables.
    """
    from ai.pipeline import EdgeAIPipeline

    processing_state["is_running"] = True
    processing_state["progress"] = 0.0
    processing_state["status_message"] = "Initializing Edge AI perception..."

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    adapter = BackendIngestAdapter()

    def on_progress(p, cur, tot):
        processing_state["progress"] = round(p * 100, 1)
        processing_state["current_frame"] = cur
        processing_state["total_frames"] = tot
        processing_state["status_message"] = f"Processing frame {cur}/{tot} ({processing_state['progress']}%)"

    async def _handle_event_async(msg):
        payload = msg.get("payload", {})
        msg_type = msg.get("type")
        async with AsyncSessionLocal() as db:
            try:
                if msg_type == "NEW_EVENT":
                    obs_payload = adapter.to_observation_payload(payload)
                    obs_create = ObservationCreate(**obs_payload)
                    await ingest_observation(db, obs_create)
                elif msg_type == "NEW_INCIDENT":
                    inc_payload = adapter.to_incident_payload(payload)
                    inc_create = IncidentCreate(**inc_payload)
                    await create_incident(db, inc_create)
            except Exception as ex:
                logger.error(f"Error persisting AI event in database: {ex}")

    def on_event(msg):
        try:
            loop.run_until_complete(_handle_event_async(msg))
        except Exception as e:
            logger.error(f"Error handling video pipeline event: {e}")

    async def _handle_telemetry_async(t_dict):
        async with AsyncSessionLocal() as db:
            try:
                telem_payload = adapter.to_telemetry_payload(t_dict)
                telem_create = TelemetryCreate(**telem_payload)
                await process_bus_telemetry(db, telem_create)
            except Exception as ex:
                logger.error(f"Error persisting bus telemetry: {ex}")

    def on_telemetry(t):
        try:
            loop.run_until_complete(_handle_telemetry_async(t))
        except Exception as e:
            logger.error(f"Error handling video pipeline telemetry: {e}")

    try:
        pipeline = EdgeAIPipeline(bus_id=bus_id)
        res = pipeline.process_video(
            video_path=video_path,
            gps_path=gps_path,
            show_window=show_window,
            delay_ms=10,
            enabled_detectors=enabled_detectors,
            on_event_callback=on_event,
            on_telemetry_callback=on_telemetry,
            on_progress_callback=on_progress,
            post_to_backend=False,  # Direct DB session ingestion via adapter
        )
        processing_state["last_result"] = res
        processing_state["status_message"] = "Processing completed successfully!"
    except Exception as e:
        processing_state["status_message"] = f"Processing error: {str(e)}"
        logger.error(f"Pipeline task failure: {e}", exc_info=True)
    finally:
        processing_state["is_running"] = False
        loop.close()
