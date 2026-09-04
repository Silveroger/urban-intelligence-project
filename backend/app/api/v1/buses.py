from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.bus import Bus
from app.schemas.telemetry import BusResponse
from app.utils.timestamps import ensure_iso_timestamp

router = APIRouter()


@router.get("", response_model=List[BusResponse], summary="List fleet buses with their latest positions")
async def get_buses(db: AsyncSession = Depends(get_db)):
    stmt = select(Bus).where(Bus.status == "active")
    res = await db.execute(stmt)
    buses = res.scalars().all()

    response: List[BusResponse] = []
    for b in buses:
        lat = b.last_latitude if b.last_latitude is not None else 30.7333
        lng = b.last_longitude if b.last_longitude is not None else 76.7794
        ts = ensure_iso_timestamp(b.last_ping)

        response.append(
            BusResponse(
                bus_id=b.vehicle_number or str(b.bus_id),
                latitude=lat,
                longitude=lng,
                heading_deg=None,
                timestamp=ts,
                status=b.status or "active",
            )
        )

    return response
