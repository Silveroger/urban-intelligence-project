"""
SIH 26124 — Incidents REST Endpoints
Conforms strictly to docs/API_CONTRACT.md (§2.4).
"""

from typing import List
from fastapi import APIRouter
from backend.app.models.incident import Incident
from backend.app.services.aggregation import obs_store

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=List[Incident])
async def get_incidents():
    """
    Returns active vehicle incidents (rash driving, hit-and-run, illegal parking).
    """
    return obs_store.get_incidents()
