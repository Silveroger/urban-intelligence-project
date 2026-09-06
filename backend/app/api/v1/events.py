from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from app.db.database import get_db
from app.models.observation import Observation
from app.schemas.events import EventResponse
from app.utils.severity import severity_to_int, severity_to_text
from app.utils.timestamps import ensure_iso_timestamp
from app.utils.coordinates import point_to_geojson_coords
from app.services.evidence import get_signed_evidence_url

router = APIRouter()


@router.get("", response_model=List[EventResponse], summary="List road defect and perception events")
async def get_events(
    event_type: Optional[str] = Query(default=None, description="Filter by event type"),
    road_segment_id: Optional[str] = Query(default=None, description="Filter by road segment ID"),
    min_severity: Optional[int] = Query(default=None, ge=1, le=4, description="Filter by minimum severity level (1-4)"),
    limit: int = Query(default=50, ge=1, le=200, description="Max results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Observation)
        .options(selectinload(Observation.bus))
        .where(Observation.status == "confirmed")
        .order_by(desc(Observation.observed_at))
    )

    if event_type:
        stmt = stmt.where(Observation.event_type == event_type)

    if road_segment_id:
        stmt = stmt.where(Observation.segment_id == road_segment_id)

    if min_severity is not None:
        stmt = stmt.where(Observation.severity >= min_severity)

    stmt = stmt.offset(offset).limit(limit)
    res = await db.execute(stmt)
    records = res.scalars().all()

    events: List[EventResponse] = []
    for r in records:
        sev_int = severity_to_int(r.severity)
        sev_label = severity_to_text(sev_int)
        bus_label = (r.bus.vehicle_number if r.bus and r.bus.vehicle_number else str(r.bus_id)) if r.bus_id else "UNKNOWN"

        metadata = r.metadata_json or {}
        event_id = metadata.get("event_id") or f"evt_{str(r.observation_id)}"
        class_name = r.class_name or metadata.get("class_name")
        frame_id = metadata.get("frame_id")

        # Normalize legacy or custom event_type strings to canonical literals
        raw_type = r.event_type or "road_defect"
        if raw_type in ("pothole", "crack", "defect"):
            norm_type = "road_defect"
            if not class_name:
                class_name = raw_type
        elif raw_type not in ("road_defect", "waterlogging", "traffic", "incident"):
            norm_type = "road_defect"
        else:
            norm_type = raw_type

        # Extract coordinates from PostGIS geometry, fallback to metadata/defaults
        lng, lat = point_to_geojson_coords(r.geom)
        if lat == 0.0 and lng == 0.0:
            lat = float(metadata.get("latitude", 30.7333))
            lng = float(metadata.get("longitude", 76.7794))

        # Dynamic signed URL generation to ensure URLs do not expire
        evidence_url = get_signed_evidence_url(r.evidence_uri)

        events.append(
            EventResponse(
                event_id=event_id,
                bus_id=bus_label,
                timestamp=ensure_iso_timestamp(r.observed_at),
                latitude=lat,
                longitude=lng,
                road_segment_id=str(r.segment_id) if r.segment_id else "",
                event_type=norm_type,
                class_name=class_name,
                confidence=float(r.confidence) if r.confidence is not None else 1.0,
                severity=sev_int,
                severity_label=sev_label,
                frame_id=frame_id,
                evidence_uri=evidence_url,
            )
        )

    return events
