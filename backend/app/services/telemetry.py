from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from geoalchemy2.elements import WKTElement
from app.models.bus import Bus
from app.models.gps import GPSPoint
from app.schemas.telemetry import TelemetryCreate, BusResponse, LiveBusTelemetryFrame
from app.websocket.manager import ws_manager
from app.utils.timestamps import ensure_iso_timestamp


async def process_bus_telemetry(
    db: AsyncSession,
    telemetry: TelemetryCreate,
) -> BusResponse:
    """
    Ingests bus telemetry, records high-frequency GPS trace, updates current bus location,
    and broadcasts live telemetry to connected WebSocket clients.
    """
    now_utc = datetime.now(timezone.utc)
    recorded_at_str = ensure_iso_timestamp(telemetry.timestamp)
    try:
        recorded_at_dt = datetime.fromisoformat(recorded_at_str)
    except Exception:
        recorded_at_dt = now_utc

    # 1. Resolve or create Bus entity
    bus_id_str = telemetry.bus_id.strip()
    bus = None

    stmt = select(Bus).where(Bus.bus_id == bus_id_str)
    res = await db.execute(stmt)
    bus = res.scalar_one_or_none()

    if not bus:
        stmt = select(Bus).where(Bus.vehicle_number == bus_id_str)
        res = await db.execute(stmt)
        bus = res.scalar_one_or_none()

    if not bus:
        bus = Bus(
            bus_id=bus_id_str,
            vehicle_number=bus_id_str,
            status="active",
            last_latitude=telemetry.latitude,
            last_longitude=telemetry.longitude,
            last_ping=recorded_at_dt,
        )
        db.add(bus)
        await db.flush()
    else:
        bus.last_latitude = telemetry.latitude
        bus.last_longitude = telemetry.longitude
        bus.last_ping = recorded_at_dt

    # 2. Record GPS Point
    point_geom = WKTElement(f"SRID=4326;POINT({telemetry.longitude} {telemetry.latitude})")
    gps_point = GPSPoint(
        bus_id=bus.bus_id,
        geom=point_geom,
        heading_deg=telemetry.heading_deg,
        speed_kmh=telemetry.speed_kmh,
        accuracy_meters=telemetry.accuracy_meters,
        recorded_at=recorded_at_dt,
    )
    db.add(gps_point)
    await db.commit()

    # 3. Construct response and broadcast
    bus_response = BusResponse(
        bus_id=str(bus.bus_id),
        vehicle_number=bus.vehicle_number,
        latitude=telemetry.latitude,
        longitude=telemetry.longitude,
        heading_deg=telemetry.heading_deg,
        timestamp=recorded_at_str,
        status=bus.status or "active",
    )

    frame = LiveBusTelemetryFrame(payload=bus_response)
    await ws_manager.broadcast(frame.model_dump())

    return bus_response
