from typing import List, Optional
from pydantic import BaseModel, Field


class RoadSegmentProperties(BaseModel):
    segment_id: str
    name: Optional[str] = None
    condition_score: float = Field(..., description="Current aggregated health score (0-100)")
    confidence: float = Field(default=1.0, description="Overall confidence metric")
    pothole_count: int = Field(default=0)
    waterlogging_count: int = Field(default=0)
    observation_count: int = Field(default=0)
    last_updated: str = Field(..., description="ISO-8601 timestamp of last observation or update")


class GeoJSONGeometry(BaseModel):
    type: str = "LineString"
    coordinates: List[List[float]] = Field(
        ..., description="Array of [longitude, latitude] coordinate pairs"
    )


class RoadSegmentFeature(BaseModel):
    type: str = "Feature"
    id: str
    geometry: GeoJSONGeometry
    properties: RoadSegmentProperties


class RoadSegmentFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[RoadSegmentFeature]


class RoadSegmentFlat(BaseModel):
    """Flat representation for direct frontend compatibility."""
    segment_id: str
    name: Optional[str] = None
    geometry: List[List[float]]
    condition_score: float
    confidence: float = 1.0
    pothole_count: int = 0
    waterlogging_count: int = 0
    observation_count: int = 0
    last_updated: str


class SegmentHistoryItem(BaseModel):
    timestamp: str
    date: str  # Frontend alias for timestamp
    condition_score: float
    score: float  # Frontend alias for condition_score
    confidence: float = 1.0
    pothole_count: int = 0
    bus_id: Optional[str] = None
