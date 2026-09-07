import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from geoalchemy2.elements import WKTElement
from app.core.config import settings
from app.models.bus import Bus
from app.models.observation import Observation
from app.schemas.observations import ObservationCreate, ObservationIngestResult, LiveEventFrame
from app.schemas.events import EventResponse
from app.services.map_matching import find_nearest_road_segment
from app.services.aggregation import recalculate_segment_metrics
from app.websocket.manager import ws_manager
from app.utils.severity import severity_to_int, severity_to_text
from app.utils.timestamps import ensure_iso_timestamp

logger = logging.getLogger("urban_intel.ingestion")


async def ingest_observation(
    db: AsyncSession,
    obs_in: ObservationCreate,
) -> ObservationIngestResult:
    """
    Executes the full observation ingestion pipeline:
    1. Validates structured AI payload.
    2. Confidence threshold check:
       - If < 0.50: Quarantines event, persists with quarantined status, skips scoring & live broadcast.
       - If >= 0.50: Confirms event, matches to road segment, updates road scoring & history, broadcasts NEW_EVENT.
    """
    now_utc = datetime.now(timezone.utc)
    recorded_at_str = ensure_iso_timestamp(obs_in.timestamp)
    try:
        recorded_at_dt = datetime.fromisoformat(recorded_at_str)
    except Exception:
        recorded_at_dt = now_utc

    # 1. Resolve Bus
    bus = None
    stmt = select(Bus).where(Bus.bus_id == obs_in.bus_id)
    res = await db.execute(stmt)
    bus = res.scalar_one_or_none()

    if not bus:
        stmt = select(Bus).where(Bus.vehicle_number == obs_in.bus_id)
        res = await db.execute(stmt)
        bus = res.scalar_one_or_none()

    bus_id_val = bus.bus_id if bus else obs_in.bus_id

    # 2. Check confidence threshold
    is_quarantined = obs_in.confidence < settings.CONFIDENCE_THRESHOLD
    obs_status = "quarantined" if is_quarantined else "confirmed"

    # 3. Map Matching
    segment_id_str = obs_in.road_segment_id
    if not segment_id_str and not is_quarantined:
        matched = await find_nearest_road_segment(db, obs_in.latitude, obs_in.longitude)
        if matched:
            segment_id_str = matched[0]

    # 4. Prepare Observation entity
    obs_id = obs_in.event_id or f"evt_{uuid.uuid4().hex[:12]}"
    point_geom = WKTElement(f"SRID=4326;POINT({obs_in.longitude} {obs_in.latitude})")
    sev_int = severity_to_int(obs_in.severity)
    sev_label = severity_to_text(sev_int)

    metadata_dict = {
        "event_id": obs_in.event_id,
        "class_name": obs_in.class_name,
        "frame_id": obs_in.frame_id,
        "track_id": obs_in.track_id,
        "plate_text": obs_in.plate_text,
        "plate_confidence": obs_in.plate_confidence,
        "latitude": obs_in.latitude,
        "longitude": obs_in.longitude,
    }
    if obs_in.metadata:
        metadata_dict.update(obs_in.metadata)

    if obs_in.risk_score is not None:
        metadata_dict["risk_score"] = obs_in.risk_score
    if obs_in.risk_level is not None:
        metadata_dict["risk_level"] = obs_in.risk_level
    if obs_in.breadth_cm is not None:
        metadata_dict["breadth_cm"] = obs_in.breadth_cm
    if obs_in.depth_cm is not None:
        metadata_dict["depth_cm"] = obs_in.depth_cm
    if obs_in.dimensions is not None:
        metadata_dict["dimensions"] = obs_in.dimensions
    if obs_in.risk_assessment is not None:
        metadata_dict["risk_assessment"] = obs_in.risk_assessment

    observation = Observation(
        observation_id=obs_id,
        bus_id=bus_id_val,
        segment_id=segment_id_str,
        geom=point_geom,
        event_type=obs_in.event_type,
        class_name=obs_in.class_name,
        confidence=obs_in.confidence,
        severity=sev_int,
        evidence_uri=obs_in.evidence_uri,
        observed_at=recorded_at_dt,
        metadata_json=metadata_dict,
        status=obs_status,
        created_at=now_utc,
    )
    db.add(observation)
    await db.commit()

    # 5. Handle Quarantined Observation
    if is_quarantined:
        logger.info(
            f"Observation {obs_in.event_id} quarantined due to low confidence ({obs_in.confidence:.2f} < {settings.CONFIDENCE_THRESHOLD})"
        )
        return ObservationIngestResult(
            status="quarantined",
            event_id=obs_in.event_id,
            observation_id=str(obs_id),
            road_segment_id=segment_id_str,
            quarantined=True,
            message="Observation quarantined due to confidence below threshold (0.50). Road scores unchanged.",
        )

    # 6. Recalculate road segment metrics and history
    if segment_id_str:
        try:
            await recalculate_segment_metrics(db, segment_id_str, bus_id_val)
        except Exception as e:
            logger.error(f"Error recalculating metrics for segment {segment_id_str}: {e}")

    # 7. Broadcast live event via WebSocket
    event_response = EventResponse(
        event_id=obs_in.event_id,
        bus_id=bus.vehicle_number if bus and bus.vehicle_number else obs_in.bus_id,
        timestamp=recorded_at_str,
        latitude=obs_in.latitude,
        longitude=obs_in.longitude,
        road_segment_id=segment_id_str or "",
        event_type=obs_in.event_type,
        class_name=obs_in.class_name,
        confidence=obs_in.confidence,
        severity=sev_int,
        severity_label=sev_label,
        frame_id=obs_in.frame_id,
        evidence_uri=obs_in.evidence_uri,
        risk_score=metadata_dict.get("risk_score"),
        risk_level=metadata_dict.get("risk_level"),
        breadth_cm=metadata_dict.get("breadth_cm"),
        depth_cm=metadata_dict.get("depth_cm"),
        dimensions=metadata_dict.get("dimensions"),
        risk_assessment=metadata_dict.get("risk_assessment"),
        metadata=metadata_dict,
    )

    frame = LiveEventFrame(payload=event_response)
    await ws_manager.broadcast(frame.model_dump())

    return ObservationIngestResult(
        status="confirmed",
        event_id=obs_in.event_id,
        observation_id=str(obs_id),
        road_segment_id=segment_id_str,
        quarantined=False,
        message="Observation ingested and road health metrics updated.",
    )
