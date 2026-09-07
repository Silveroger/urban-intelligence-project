from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.telemetry import TelemetryCreate, BusResponse
from app.services.telemetry import process_bus_telemetry

router = APIRouter()


@router.post(
    "",
    response_model=BusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest bus GPS telemetry",
)
async def post_telemetry(
    telemetry: TelemetryCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Ingests bus telemetry:
    - Validates latitude & longitude.
    - Records high-frequency GPS trace into gps_points.
    - Updates latest bus position in buses table.
    - Broadcasts BUS_TELEMETRY frame via WebSocket to /ws/live.
    """
    telemetry.validate_geo()
    return await process_bus_telemetry(db, telemetry)
