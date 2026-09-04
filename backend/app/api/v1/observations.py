from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.observations import ObservationCreate, ObservationIngestResult
from app.services.ingestion import ingest_observation

router = APIRouter()


@router.post(
    "",
    response_model=ObservationIngestResult,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest AI edge perception observation",
)
async def post_observation(
    obs_in: ObservationCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Ingests AI observation:
    - Validates schema and coordinates.
    - OCR verification: plate_text requires plate_confidence.
    - Confidence threshold (< 0.50 quarantined, >= 0.50 processed & broadcast).
    - Map-matches to road network, updates road scoring, and broadcasts NEW_EVENT live.
    """
    return await ingest_observation(db, obs_in)
