"""
SIH 26124 — Urban Analytics Endpoints
Provides traffic congestion summaries, infrastructure gap KPIs, and route health.
Conforms to docs/PRD.md (§5).
"""

from typing import Dict, List
from fastapi import APIRouter
from backend.app.services.aggregation import obs_store
from backend.app.services.spatial_engine import spatial_engine

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
async def get_analytics_summary() -> Dict:
    """
    Returns high-level platform statistics and KPIs.
    """
    feats = list(spatial_engine.segments.values())
    total_segments = len(feats)
    critical_segments = sum(1 for f in feats if f["properties"]["condition_score"] < 60.0)
    total_potholes = sum(f["properties"]["pothole_count"] for f in feats)
    total_waterlogging = sum(f["properties"]["waterlogging_count"] for f in feats)

    events = obs_store.get_events()
    incidents = obs_store.get_incidents()
    buses = obs_store.get_buses()

    return {
        "total_road_segments": total_segments,
        "critical_issues": critical_segments + len([e for e in events if (e.get("severity") or 1) >= 3]),
        "monitored_buses": len(buses),
        "active_incidents": len(incidents),
        "potholes_detected": total_potholes,
        "waterlogging_zones": total_waterlogging,
        "avg_network_condition": round(sum(f["properties"]["condition_score"] for f in feats) / max(1, total_segments), 1)
    }
