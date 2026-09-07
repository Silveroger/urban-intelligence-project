from typing import Optional
from pydantic import BaseModel, Field
from app.utils.coordinates import validate_coordinates


class TelemetryCreate(BaseModel):
    bus_id: str = Field(..., description="Bus identifier (UUID or vehicle number)")
    latitude: float
    longitude: float
    speed_kmh: Optional[float] = None
    heading_deg: Optional[float] = None
    accuracy_meters: Optional[float] = None
    timestamp: Optional[str] = None

    def validate_geo(self) -> None:
        validate_coordinates(self.latitude, self.longitude)


class BusResponse(BaseModel):
    bus_id: str
    latitude: float
    longitude: float
    heading_deg: Optional[float] = None
    timestamp: str
    status: Optional[str] = "active"
    vehicle_number: Optional[str] = None


class LiveBusTelemetryFrame(BaseModel):
    type: str = "BUS_TELEMETRY"
    payload: BusResponse
