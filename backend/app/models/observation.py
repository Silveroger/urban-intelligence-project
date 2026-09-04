from datetime import datetime, timezone
from sqlalchemy import Column, String, SmallInteger, Numeric, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.db.database import Base


class Observation(Base):
    __tablename__ = "observations"

    observation_id = Column(String(64), primary_key=True)
    bus_id = Column(String(64), ForeignKey("buses.bus_id", ondelete="SET NULL"), nullable=True, index=True)
    segment_id = Column(String(64), ForeignKey("road_segments.segment_id", ondelete="SET NULL"), nullable=True, index=True)
    geom = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    event_type = Column(String(32), nullable=False)
    class_name = Column(String(64), nullable=True)
    confidence = Column(Numeric(3, 2), nullable=False)
    severity = Column(SmallInteger, nullable=True, default=1)
    evidence_uri = Column(String(512), nullable=True)
    observed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Auxiliary columns for metadata & edge validation
    metadata_json = Column("metadata", JSONB, nullable=True)
    status = Column(String(32), default="confirmed")

    __table_args__ = (
        CheckConstraint("severity BETWEEN 1 AND 4", name="chk_observations_severity"),
    )

    bus = relationship("Bus", back_populates="observations")
    road_segment = relationship("RoadSegment", back_populates="observations")
    incidents = relationship("Incident", back_populates="observation")

    # Backward-compatibility property aliases
    @property
    def id(self):
        return self.observation_id

    @id.setter
    def id(self, val):
        self.observation_id = str(val) if val is not None else None

    @property
    def road_segment_id(self):
        return self.segment_id

    @road_segment_id.setter
    def road_segment_id(self, val):
        self.segment_id = str(val) if val is not None else None

    @property
    def observation_type(self):
        return self.event_type

    @observation_type.setter
    def observation_type(self, val):
        self.event_type = val

    @property
    def detected_at(self):
        return self.observed_at

    @detected_at.setter
    def detected_at(self, val):
        self.observed_at = val

    @property
    def evidence_path(self):
        return self.evidence_uri

    @evidence_path.setter
    def evidence_path(self, val):
        self.evidence_uri = val

    @property
    def location(self):
        return self.geom

    @location.setter
    def location(self, val):
        self.geom = val
