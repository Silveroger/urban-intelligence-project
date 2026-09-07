from typing import Optional, Union
from pydantic import BaseModel, Field, model_validator


class IncidentResponse(BaseModel):
    incident_id: str
    incident_type: str
    severity: int = Field(default=1, ge=1, le=4, description="Numeric severity: 1 to 4")
    severity_label: Optional[str] = Field(default=None, description="Optional descriptive severity label: low, moderate, high, critical")
    incident_score: Optional[float] = Field(default=None, description="Normalized score 0-100 derived from severity")
    vehicle_track_id: Optional[str] = None
    plate_text: Optional[str] = None
    plate_confidence: Optional[float] = None
    latitude: float
    longitude: float
    timestamp: str
    road_segment_id: Optional[str] = None
    observation_id: Optional[str] = None
    evidence_uri: Optional[str] = None
    description: Optional[str] = None
    status: str = "open"


class IncidentCreate(BaseModel):
    incident_id: Optional[str] = None
    incident_type: str
    severity: Optional[Union[int, str]] = 1
    latitude: float
    longitude: float
    timestamp: Optional[str] = None
    bus_id: Optional[str] = None
    road_segment_id: Optional[str] = None
    observation_id: Optional[str] = None
    description: Optional[str] = None
    vehicle_track_id: Optional[str] = None
    plate_text: Optional[str] = None
    plate_confidence: Optional[float] = None
    evidence_uri: Optional[str] = None

    @model_validator(mode="after")
    def validate_ocr_rules(self) -> "IncidentCreate":
        if self.plate_text and self.plate_confidence is None:
            raise ValueError("plate_confidence is required whenever plate_text is provided")
        return self
