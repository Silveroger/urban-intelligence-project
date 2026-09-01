"""
SIH 26124 — Road Segments REST Endpoints
Conforms strictly to docs/API_CONTRACT.md (§2.1, §2.2).
"""

from typing import List
from fastapi import APIRouter, HTTPException
from backend.app.models.segment import RoadSegmentFeatureCollection, SegmentHistoryItem
from backend.app.services.spatial_engine import spatial_engine

router = APIRouter(prefix="/segments", tags=["segments"])


@router.get("/geojson", response_model=RoadSegmentFeatureCollection)
async def get_segments_geojson():
    """
    Returns the complete road network with current aggregate condition scores.
    """
    return spatial_engine.get_feature_collection()


@router.get("/{segment_id}/history", response_model=List[SegmentHistoryItem])
async def get_segment_history(segment_id: str):
    """
    Returns historical condition degradation passes for a specific road segment.
    """
    hist = spatial_engine.get_segment_history(segment_id)
    if not hist:
        raise HTTPException(status_code=404, detail=f"Road segment '{segment_id}' not found")
    return hist
