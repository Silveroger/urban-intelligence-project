"""
SQLAlchemy ORM models mapped to the existing Supabase schema.
"""
from app.models.bus import Bus
from app.models.gps import GPSPoint
from app.models.road_segment import RoadSegment
from app.models.observation import Observation
from app.models.incident import Incident
from app.models.segment_history import SegmentHistory

__all__ = [
    "Bus",
    "GPSPoint",
    "RoadSegment",
    "Observation",
    "Incident",
    "SegmentHistory",
]
