from typing import Optional, Union, Literal
from pydantic import BaseModel, Field, model_validator
from app.utils.coordinates import validate_coordinates
from app.utils.severity import severity_to_text, severity_to_int
from app.schemas.events import EventResponse


class ObservationCreate(BaseModel):
    event_id: str = Field(..., description="Unique deterministic identifier, e.g. evt_20260831_101_0042")
    bus_id: str = Field(..., description="Identifier of sensing fleet vehicle")
    timestamp: str = Field(..., description="ISO-8601 capture timestamp with timezone")
    latitude: float
    longitude: float
    road_segment_id: Optional[str] = None
    event_type: Literal["road_defect", "waterlogging", "traffic", "incident"]
    class_name: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    severity: Optional[Union[int, str]] = 1
    frame_id: Optional[int] = None
    track_id: Optional[str] = None
    plate_text: Optional[str] = None
    plate_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    evidence_uri: Optional[str] = None
    metadata: Optional[dict] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    breadth_cm: Optional[float] = None
    depth_cm: Optional[float] = None
    dimensions: Optional[dict] = None
    risk_assessment: Optional[str] = None

    @model_validator(mode="after")
    def validate_rules(self) -> "ObservationCreate":
        # Coordinate boundary check
        validate_coordinates(self.latitude, self.longitude)

        # OCR Rule: plate_text requires plate_confidence
        if self.plate_text and self.plate_confidence is None:
            raise ValueError("OCR output error: plate_text was provided without an associated plate_confidence score")

        return self


class ObservationIngestResult(BaseModel):
    status: str = Field(..., description="'confirmed' or 'quarantined'")
    event_id: str
    observation_id: str
    road_segment_id: Optional[str] = None
    quarantined: bool
    message: str


from app.schemas.incidents import IncidentResponse


class LiveEventFrame(BaseModel):
    type: str = "NEW_EVENT"
    payload: EventResponse


class LiveIncidentFrame(BaseModel):
    type: str = "NEW_INCIDENT"
    payload: IncidentResponse


class SegmentUpdatePayload(BaseModel):
    segment_id: str
    condition_score: Optional[float] = None
    pothole_count: int = 0
    waterlogging_count: int = 0
    observation_count: int = 0
    last_updated: Optional[str] = None


class LiveSegmentUpdateFrame(BaseModel):
    type: str = "SEGMENT_UPDATE"
    payload: SegmentUpdatePayload
