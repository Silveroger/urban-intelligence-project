from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime
from sqlalchemy.orm import relationship
from app.db.database import Base


class Bus(Base):
    __tablename__ = "buses"

    bus_id = Column(String(64), primary_key=True)
    vehicle_number = Column(String(32), nullable=True, index=True)
    route_id = Column(String(64), nullable=True)
    status = Column(String(32), default="active", index=True)
    last_ping = Column(DateTime(timezone=True), nullable=True)

    # Auxiliary columns for fleet monitoring
    last_latitude = Column(Float, nullable=True)
    last_longitude = Column(Float, nullable=True)

    gps_points = relationship("GPSPoint", back_populates="bus", cascade="all, delete-orphan")
    observations = relationship("Observation", back_populates="bus")

    # Backward-compatibility property aliases
    @property
    def id(self):
        return self.bus_id

    @id.setter
    def id(self, val):
        self.bus_id = str(val) if val is not None else None

    @property
    def last_seen_at(self):
        return self.last_ping

    @last_seen_at.setter
    def last_seen_at(self, val):
        self.last_ping = val
