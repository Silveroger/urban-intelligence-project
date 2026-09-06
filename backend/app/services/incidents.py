import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.elements import WKTElement
from app.models.incident import Incident
from app.schemas.incidents import IncidentCreate, IncidentResponse
from app.schemas.observations import LiveIncidentFrame
from app.services.map_matching import find_nearest_road_segment
from app.services.evidence import get_signed_evidence_url
from app.websocket.manager import ws_manager
from app.utils.severity import severity_to_int, severity_to_text
from app.utils.timestamps import ensure_iso_timestamp


async def create_incident(
    db: AsyncSession,
    incident_in: IncidentCreate,
) -> IncidentResponse:
    """
    Creates an incident record, optionally map-matching to road segment if not specified.
    Preserves foreign-key relationships to road_segments and observations.
    """
    now_utc = datetime.now(timezone.utc)

    # 1. Map matching if road_segment_id is not provided
    segment_id_str = incident_in.road_segment_id
    if not segment_id_str:
        match_res = await find_nearest_road_segment(db, incident_in.latitude, incident_in.longitude)
        if match_res:
            segment_id_str = match_res[0]

    # 2. Normalize severity to SMALLINT (1-4)
    sev_num = severity_to_int(incident_in.severity)
    sev_label = severity_to_text(sev_num)

    # 3. Create Incident model with documented columns
    inc_id = f"inc_{uuid.uuid4().hex[:12]}"
    point_geom = WKTElement(f"SRID=4326;POINT({incident_in.longitude} {incident_in.latitude})")

    incident = Incident(
        incident_id=inc_id,
        road_segment_id=segment_id_str,
        observation_id=incident_in.observation_id,
        incident_type=incident_in.incident_type,
        severity=sev_num,
        status="open",
        geom=point_geom,
        description=incident_in.description,
        vehicle_track_id=incident_in.vehicle_track_id,
        plate_text=incident_in.plate_text,
        plate_confidence=incident_in.plate_confidence,
        evidence_uri=incident_in.evidence_uri,
        recorded_at=now_utc,
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)

    signed_evidence = get_signed_evidence_url(incident.evidence_uri) or incident.evidence_uri

    resp = IncidentResponse(
        incident_id=incident.incident_id,
        incident_type=incident.incident_type,
        severity=sev_num,
        severity_label=sev_label,
        incident_score=round(sev_num * 25.0, 1),
        vehicle_track_id=incident.vehicle_track_id,
        plate_text=incident.plate_text,
        plate_confidence=float(incident.plate_confidence) if incident.plate_confidence is not None else None,
        latitude=incident_in.latitude,
        longitude=incident_in.longitude,
        timestamp=ensure_iso_timestamp(incident.recorded_at),
        road_segment_id=str(incident.road_segment_id) if incident.road_segment_id else None,
        observation_id=str(incident.observation_id) if incident.observation_id else None,
        evidence_uri=signed_evidence,
        description=incident.description,
        status=incident.status,
    )

    frame = LiveIncidentFrame(payload=resp)
    await ws_manager.broadcast(frame.model_dump())

    return resp
