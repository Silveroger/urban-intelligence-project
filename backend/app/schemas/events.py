from typing import Optional, Literal
from pydantic import BaseModel, Field


class EventResponse(BaseModel):
    event_id: str
    bus_id: str
    timestamp: str
    latitude: float
    longitude: float
    road_segment_id: str
    event_type: Literal["road_defect", "waterlogging", "traffic", "incident"]
    class_name: Optional[str] = None
    confidence: float
    severity: int = Field(..., ge=1, le=4, description="Numeric severity: 1 (Low), 2 (Moderate), 3 (High), 4 (Critical)")
    severity_label: Optional[str] = Field(default=None, description="Descriptive severity label for display only: low, moderate, high, critical")
    frame_id: Optional[int] = None
    evidence_uri: Optional[str] = None
