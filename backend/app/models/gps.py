from datetime import datetime, timezone
from sqlalchemy import Column, BigInteger, String, Float, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.db.database import Base


class GPSPoint(Base):
    __tablename__ = "gps_points"

    point_id = Column(BigInteger, primary_key=True, autoincrement=True)
    bus_id = Column(String(64), ForeignKey("buses.bus_id", ondelete="CASCADE"), nullable=False, index=True)
    geom = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    heading_deg = Column(Numeric(5, 2), nullable=True)
    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Auxiliary columns for raw telemetry
    speed_kmh = Column(Float, nullable=True)
    accuracy_meters = Column(Float, nullable=True)

    bus = relationship("Bus", back_populates="gps_points")

    # Backward-compatibility property aliases
    @property
    def id(self):
        return self.point_id

    @property
    def heading(self):
        return float(self.heading_deg) if self.heading_deg is not None else None

    @heading.setter
    def heading(self, val):
        self.heading_deg = val

    @property
    def location(self):
        return self.geom

    @location.setter
    def location(self, val):
        self.geom = val
