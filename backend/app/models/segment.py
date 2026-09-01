"""
SIH 26124 — Road Segment & Spatial GeoJSON Schemas
Conforms strictly to docs/API_CONTRACT.md (§2.1, §2.2) and docs/DATABASE_SCHEMA.md.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SegmentProperties(BaseModel):
    segment_id: str
    name: str
    condition_score: float = Field(ge=0.0, le=100.0)
    confidence: float = Field(ge=0.0, le=1.0)
    pothole_count: int = 0
    waterlogging_count: int = 0
    observation_count: int = 0
    last_updated: str


class GeoJSONGeometry(BaseModel):
    type: str = "LineString"
    coordinates: List[List[float]]  # GeoJSON [longitude, latitude]


class RoadSegmentFeature(BaseModel):
    type: str = "Feature"
    id: str
    geometry: GeoJSONGeometry
    properties: SegmentProperties


class RoadSegmentFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[RoadSegmentFeature]


class SegmentHistoryItem(BaseModel):
    timestamp: str
    condition_score: float
    confidence: float
    pothole_count: int
    bus_id: Optional[str] = None
