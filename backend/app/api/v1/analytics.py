from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from app.db.database import get_db
from app.models.road_segment import RoadSegment
from app.models.bus import Bus
from app.models.observation import Observation
from app.models.incident import Incident

router = APIRouter()


class ConditionDistribution(BaseModel):
    healthy: int = 0
    moderate: int = 0
    poor: int = 0
    critical: int = 0


class AnalyticsSummaryResponse(BaseModel):
    total_segments: int
    average_condition_score: float
    critical_segments_count: int
    active_buses_count: int
    total_events_count: int
    total_incidents_count: int
    condition_distribution: ConditionDistribution


@router.get("/summary", response_model=AnalyticsSummaryResponse, summary="Get high-level city infrastructure analytics summary")
async def get_analytics_summary(db: AsyncSession = Depends(get_db)):
    """
    Returns aggregated city-wide infrastructure and perception KPIs.
    """
    # 1. Segment condition analytics
    seg_res = await db.execute(select(RoadSegment.condition_score))
    scores = [float(row[0]) for row in seg_res.all() if row[0] is not None]

    total_segments = len(scores)
    avg_score = round(sum(scores) / total_segments, 1) if total_segments > 0 else 100.0

    healthy = sum(1 for s in scores if s >= 80)
    moderate = sum(1 for s in scores if 60 <= s < 80)
    poor = sum(1 for s in scores if 40 <= s < 60)
    critical = sum(1 for s in scores if s < 40)

    # 2. Active fleet count
    bus_res = await db.execute(select(func.count(Bus.bus_id)).where(Bus.status == "active"))
    active_buses = bus_res.scalar() or 0

    # 3. Confirmed perception defect observations
    obs_res = await db.execute(select(func.count(Observation.observation_id)).where(Observation.status == "confirmed"))
    total_events = obs_res.scalar() or 0

    # 4. Total traffic incidents
    inc_res = await db.execute(select(func.count(Incident.incident_id)))
    total_incidents = inc_res.scalar() or 0

    return AnalyticsSummaryResponse(
        total_segments=total_segments,
        average_condition_score=avg_score,
        critical_segments_count=critical,
        active_buses_count=active_buses,
        total_events_count=total_events,
        total_incidents_count=total_incidents,
        condition_distribution=ConditionDistribution(
            healthy=healthy,
            moderate=moderate,
            poor=poor,
            critical=critical,
        ),
    )
