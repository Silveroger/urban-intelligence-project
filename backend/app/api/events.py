"""
SIH 26124 — Events REST Endpoints
Conforms strictly to docs/API_CONTRACT.md (§2.3).
"""

from typing import List, Optional
from fastapi import APIRouter, Query
from backend.app.models.event import ObservationEvent
from backend.app.services.aggregation import obs_store

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=List[ObservationEvent])
async def get_events(
    event_type: Optional[str] = Query(default=None),
    min_severity: Optional[int] = Query(default=None, ge=1, le=4)
):
    """
    Returns active road defects, waterlogging, traffic and hazard observations.
    """
    return obs_store.get_events(event_type=event_type, min_severity=min_severity)
