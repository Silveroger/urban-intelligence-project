"""
SIH 26124 — Observation & Perception Event Schemas
Conforms strictly to docs/AI_CONTRACT.md and docs/API_CONTRACT.md (§2.3).
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class EventType(str, Enum):
    ROAD_DEFECT = "road_defect"
    WATERLOGGING = "waterlogging"
    TRAFFIC = "traffic"
    INCIDENT = "incident"
    INFRASTRUCTURE = "infrastructure"
    PEDESTRIAN = "pedestrian"


class ObservationEvent(BaseModel):
    event_id: str
    bus_id: str
    timestamp: str
    latitude: float
    longitude: float
    road_segment_id: Optional[str] = None
    event_type: EventType
    class_name: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    severity: Optional[int] = Field(default=1, ge=1, le=4)
    frame_id: Optional[int] = None
    evidence_uri: Optional[str] = None
