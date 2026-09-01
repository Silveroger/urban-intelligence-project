"""
SIH 26124 — Fleet Buses REST Endpoints
Conforms strictly to docs/API_CONTRACT.md (§2.5).
"""

from typing import List
from fastapi import APIRouter
from backend.app.models.telemetry import BusTelemetry
from backend.app.services.aggregation import obs_store

router = APIRouter(prefix="/buses", tags=["buses"])


@router.get("", response_model=List[BusTelemetry])
async def get_buses():
    """
    Returns latest GPS telemetry and heading for all active fleet buses.
    """
    return obs_store.get_buses()
