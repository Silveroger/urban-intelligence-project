from datetime import datetime, timezone
from typing import Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.road_segment import RoadSegment
from app.models.observation import Observation
from app.models.segment_history import SegmentHistory
from app.services.scoring import calculate_road_health
from app.websocket.manager import ws_manager
from app.schemas.observations import LiveSegmentUpdateFrame, SegmentUpdatePayload
from app.utils.timestamps import ensure_iso_timestamp


async def recalculate_segment_metrics(
    db: AsyncSession,
    segment_id: Union[str, any],
    bus_id: Optional[str] = None,
) -> Optional[RoadSegment]:
    """
    Recalculates condition score, defect counts, updates road_segments table,
    and inserts an immutable historical snapshot into segment_history.
    """
    seg_id_str = str(segment_id)

    # 1. Fetch all confirmed observations for this segment
    obs_query = select(Observation).where(
        Observation.segment_id == seg_id_str,
        Observation.status == "confirmed",
    ).order_by(desc(Observation.observed_at))
    
    res = await db.execute(obs_query)
    observations = res.scalars().all()

    # 2. Count defects by category
    pothole_count = 0
    crack_count = 0
    rough_surface_count = 0
    waterlogging_count = 0

    obs_dicts = []
    latest_observed_at = None

    for obs in observations:
        if latest_observed_at is None or (obs.observed_at and obs.observed_at > latest_observed_at):
            latest_observed_at = obs.observed_at

        class_name = str(obs.class_name or "").lower()
        obs_type = str(obs.event_type or "").lower()

        if "pothole" in class_name or "pothole" in obs_type:
            pothole_count += 1
        if "crack" in class_name or "crack" in obs_type:
            crack_count += 1
        if "rough" in class_name or "wear" in class_name:
            rough_surface_count += 1
        if "water" in class_name or "waterlogging" in obs_type:
            waterlogging_count += 1

        obs_dicts.append({
            "observation_type": obs.event_type,
            "severity": obs.severity,
            "confidence": float(obs.confidence) if obs.confidence is not None else 1.0,
        })

    # 3. Calculate health score and condition
    new_health_score, new_condition = calculate_road_health(obs_dicts, weight_by_confidence=True)
    total_observations = len(observations)
    now_utc = datetime.now(timezone.utc)

    # 4. Update the RoadSegment record
    seg_stmt = select(RoadSegment).where(RoadSegment.segment_id == seg_id_str)
    seg_res = await db.execute(seg_stmt)
    segment = seg_res.scalar_one_or_none()

    if segment:
        segment.condition_score = new_health_score
        segment.observation_count = total_observations
        segment.pothole_count = pothole_count
        segment.waterlogging_count = waterlogging_count
        segment.last_updated = latest_observed_at or now_utc

        # 5. Debounced history snapshot insertion (BUG-006)
        hist_stmt = (
            select(SegmentHistory)
            .where(SegmentHistory.segment_id == seg_id_str)
            .order_by(desc(SegmentHistory.recorded_at))
            .limit(1)
        )
        hist_res = await db.execute(hist_stmt)
        latest_hist = hist_res.scalar_one_or_none()

        should_insert = True
        if latest_hist and latest_hist.recorded_at:
            rec_dt = latest_hist.recorded_at
            if rec_dt.tzinfo is None:
                rec_dt = rec_dt.replace(tzinfo=timezone.utc)
            if (now_utc - rec_dt).total_seconds() < 10.0:
                should_insert = False
                latest_hist.condition_score = new_health_score
                latest_hist.pothole_count = pothole_count
                latest_hist.waterlogging_count = waterlogging_count
                latest_hist.confidence = segment.confidence or 1.00
                if bus_id:
                    latest_hist.bus_id = str(bus_id)
                latest_hist.recorded_at = now_utc

        if should_insert:
            history_record = SegmentHistory(
                segment_id=seg_id_str,
                condition_score=new_health_score,
                confidence=segment.confidence or 1.00,
                pothole_count=pothole_count,
                waterlogging_count=waterlogging_count,
                bus_id=str(bus_id) if bus_id else None,
                recorded_at=now_utc,
            )
            db.add(history_record)

        await db.commit()
        await db.refresh(segment)

        # 6. Broadcast segment update (BUG-017)
        frame = LiveSegmentUpdateFrame(
            payload=SegmentUpdatePayload(
                segment_id=segment.segment_id,
                condition_score=float(segment.condition_score) if segment.condition_score is not None else None,
                pothole_count=segment.pothole_count or 0,
                waterlogging_count=segment.waterlogging_count or 0,
                observation_count=segment.observation_count or 0,
                last_updated=ensure_iso_timestamp(segment.last_updated),
            )
        )
        await ws_manager.broadcast(frame.model_dump())

    return segment
