from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.database import get_db
from app.models.incident import Incident
from app.schemas.incidents import IncidentResponse, IncidentCreate
from app.services.incidents import create_incident
from app.services.evidence import get_signed_evidence_url
from app.utils.severity import severity_to_int, severity_to_text
from app.utils.timestamps import ensure_iso_timestamp
from app.utils.coordinates import point_to_geojson_coords

router = APIRouter()


@router.get("", response_model=List[IncidentResponse], summary="List traffic incidents and violations")
async def get_incidents(
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Incident).order_by(desc(Incident.recorded_at)).offset(offset).limit(limit)
    if status_filter:
        stmt = stmt.where(Incident.status == status_filter)

    res = await db.execute(stmt)
    records = res.scalars().all()

    incidents: List[IncidentResponse] = []
    for inc in records:
        sev_num = severity_to_int(inc.severity)
        sev_label = severity_to_text(sev_num)

        lng, lat = point_to_geojson_coords(inc.geom)
        if lat == 0.0 and lng == 0.0:
            lat = 30.7350
            lng = 76.7820

        incidents.append(
            IncidentResponse(
                incident_id=str(inc.incident_id),
                incident_type=inc.incident_type,
                severity=sev_num,
                severity_label=sev_label,
                incident_score=round(sev_num * 25.0, 1),
                vehicle_track_id=inc.vehicle_track_id,
                plate_text=inc.plate_text,
                plate_confidence=float(inc.plate_confidence) if inc.plate_confidence is not None else None,
                latitude=lat,
                longitude=lng,
                timestamp=ensure_iso_timestamp(inc.recorded_at),
                road_segment_id=str(inc.road_segment_id) if inc.road_segment_id else None,
                observation_id=str(inc.observation_id) if inc.observation_id else None,
                evidence_uri=get_signed_evidence_url(inc.evidence_uri) or inc.evidence_uri,
                description=inc.description,
                status=inc.status or "open",
            )
        )

    return incidents


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED, summary="Create a new traffic incident")
async def post_incident(
    incident_in: IncidentCreate,
    db: AsyncSession = Depends(get_db),
):
    return await create_incident(db, incident_in)
