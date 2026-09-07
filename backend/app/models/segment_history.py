from datetime import datetime, timezone
from sqlalchemy import Column, BigInteger, String, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class SegmentHistory(Base):
    __tablename__ = "segment_history"

    history_id = Column(BigInteger, primary_key=True, autoincrement=True)
    segment_id = Column(String(64), ForeignKey("road_segments.segment_id", ondelete="CASCADE"), nullable=False, index=True)
    condition_score = Column(Numeric(5, 2), nullable=False)
    confidence = Column(Numeric(3, 2), nullable=False, default=1.00)
    pothole_count = Column(Integer, nullable=False, default=0)
    waterlogging_count = Column(Integer, nullable=False, default=0)
    bus_id = Column(String(64), nullable=True)
    recorded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    road_segment = relationship("RoadSegment", back_populates="history")

    # Backward-compatibility property aliases
    @property
    def id(self):
        return self.history_id

    @property
    def road_segment_id(self):
        return self.segment_id

    @road_segment_id.setter
    def road_segment_id(self, val):
        self.segment_id = str(val) if val is not None else None

    @property
    def health_score(self):
        return float(self.condition_score) if self.condition_score is not None else 100.0

    @health_score.setter
    def health_score(self, val):
        self.condition_score = val
