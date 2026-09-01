"""
SIH 26124 — Fleet Bus Telemetry Schema
Conforms to docs/API_CONTRACT.md (§2.5) and ADR-007 (speed is optional).
"""

from typing import Optional
from pydantic import BaseModel, Field


class BusTelemetry(BaseModel):
    bus_id: str
    latitude: float
    longitude: float
    heading_deg: Optional[float] = None
    speed_kmh: Optional[float] = None
    timestamp: str
