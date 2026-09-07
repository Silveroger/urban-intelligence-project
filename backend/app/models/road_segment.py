from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Numeric, DateTime
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.db.database import Base


class RoadSegment(Base):
    __tablename__ = "road_segments"

    segment_id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=True)
    geom = Column(Geometry(geometry_type="LINESTRING", srid=4326), nullable=False)
    condition_score = Column(Numeric(5, 2), default=100.00)
    confidence = Column(Numeric(3, 2), default=1.00)
    pothole_count = Column(Integer, default=0)
    waterlogging_count = Column(Integer, default=0)
    observation_count = Column(Integer, default=0)
    last_updated = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    observations = relationship("Observation", back_populates="road_segment")
    history = relationship("SegmentHistory", back_populates="road_segment", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="road_segment")

    # Backward-compatibility property aliases
    @property
    def id(self):
        return self.segment_id

    @id.setter
    def id(self, val):
        self.segment_id = str(val) if val is not None else None

    @property
    def road_name(self):
        return self.name

    @road_name.setter
    def road_name(self, val):
        self.name = val

    @property
    def health_score(self):
        return float(self.condition_score) if self.condition_score is not None else 100.0

    @health_score.setter
    def health_score(self, val):
        self.condition_score = val
