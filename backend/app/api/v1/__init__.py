"""
API v1 Router module.
"""
from fastapi import APIRouter
from app.api.v1.segments import router as segments_router
from app.api.v1.events import router as events_router
from app.api.v1.incidents import router as incidents_router
from app.api.v1.buses import router as buses_router
from app.api.v1.observations import router as observations_router
from app.api.v1.telemetry import router as telemetry_router
from app.api.v1.analytics import router as analytics_router

api_v1_router = APIRouter()

api_v1_router.include_router(segments_router, prefix="/segments", tags=["Road Segments"])
api_v1_router.include_router(events_router, prefix="/events", tags=["Events & Observations"])
api_v1_router.include_router(incidents_router, prefix="/incidents", tags=["Incidents"])
api_v1_router.include_router(buses_router, prefix="/buses", tags=["Buses & Telemetry"])
api_v1_router.include_router(observations_router, prefix="/observations", tags=["Observation Ingestion"])
api_v1_router.include_router(telemetry_router, prefix="/telemetry", tags=["Telemetry Ingestion"])
api_v1_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])

