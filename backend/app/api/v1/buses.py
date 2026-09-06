from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.database import get_db
from app.models.bus import Bus
from app.models.gps import GPSPoint
from app.schemas.telemetry import BusResponse
from app.utils.timestamps import ensure_iso_timestamp

router = APIRouter()


@router.get("", response_model=List[BusResponse], summary="List fleet buses with their latest positions")
async def get_buses(db: AsyncSession = Depends(get_db)):
    latest_gps = (
        select(
            GPSPoint.bus_id,
            GPSPoint.heading_deg,
            func.row_number().over(
                partition_by=GPSPoint.bus_id,
                order_by=GPSPoint.recorded_at.desc()
            ).label("rn")
        ).subquery()
    )
    stmt = (
        select(Bus, latest_gps.c.heading_deg)
        .outerjoin(latest_gps, (Bus.bus_id == latest_gps.c.bus_id) & (latest_gps.c.rn == 1))
        .where(Bus.status == "active")
    )
    res = await db.execute(stmt)
    rows = res.all()

    response: List[BusResponse] = []
    for row in rows:
        if isinstance(row, (tuple, list)) and len(row) >= 2:
            b, heading = row[0], row[1]
        elif hasattr(row, "Bus"):
            b = row.Bus
            heading = getattr(row, "heading_deg", None)
        else:
            b = row
            heading = None

        lat = b.last_latitude if b.last_latitude is not None else 30.7333
        lng = b.last_longitude if b.last_longitude is not None else 76.7794
        ts = ensure_iso_timestamp(b.last_ping)
        hdg = float(heading) if heading is not None else None

        response.append(
            BusResponse(
                bus_id=str(b.bus_id),
                latitude=lat,
                longitude=lng,
                heading_deg=hdg,
                timestamp=ts,
                status=b.status or "active",
                vehicle_number=b.vehicle_number,
            )
        )

    return response
