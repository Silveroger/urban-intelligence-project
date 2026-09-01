"""
SIH 26124 — Incident Schemas
Conforms strictly to docs/API_CONTRACT.md (§2.4) and docs/AI_CONTRACT.md.
"""

from typing import Optional
from pydantic import BaseModel, Field


class Incident(BaseModel):
    incident_id: str
    timestamp: str
    latitude: float
    longitude: float
    incident_type: str  # illegal_parking, rash_driving, hit_and_run, lane_blockage
    severity: int = Field(default=1, ge=1, le=4)
    vehicle_track_id: Optional[str] = None
    plate_text: Optional[str] = None
    plate_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    evidence_uri: Optional[str] = None
