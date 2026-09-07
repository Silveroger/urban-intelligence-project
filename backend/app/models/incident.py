from datetime import datetime, timezone
from sqlalchemy import Column, String, SmallInteger, Numeric, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.db.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    incident_id = Column(String(64), primary_key=True)
    geom = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    incident_type = Column(String(64), nullable=False)
    severity = Column(SmallInteger, nullable=True, default=1)
    vehicle_track_id = Column(String(64), nullable=True)
    plate_text = Column(String(32), nullable=True)
    plate_confidence = Column(Numeric(3, 2), nullable=True)
    evidence_uri = Column(String(512), nullable=True)
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Foreign keys to parent entities
    road_segment_id = Column(String(64), ForeignKey("road_segments.segment_id", ondelete="SET NULL"), nullable=True, index=True)
    observation_id = Column(String(64), ForeignKey("observations.observation_id", ondelete="SET NULL"), nullable=True, index=True)

    # Auxiliary fields
    description = Column(String(512), nullable=True)
    status = Column(String(32), default="open")

    __table_args__ = (
        CheckConstraint("severity BETWEEN 1 AND 4", name="chk_incidents_severity"),
    )

    road_segment = relationship("RoadSegment", back_populates="incidents")
    observation = relationship("Observation", back_populates="incidents")

    # Backward-compatibility property aliases
    @property
    def id(self):
        return self.incident_id

    @id.setter
    def id(self, val):
        self.incident_id = str(val) if val is not None else None

    @property
    def segment_id(self):
        return self.road_segment_id

    @segment_id.setter
    def segment_id(self, val):
        self.road_segment_id = str(val) if val is not None else None

    @property
    def detected_at(self):
        return self.recorded_at

    @detected_at.setter
    def detected_at(self, val):
        self.recorded_at = val

    @property
    def location(self):
        return self.geom

    @location.setter
    def location(self, val):
        self.geom = val
