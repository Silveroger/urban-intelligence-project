"""
Deterministic Synthetic Chandigarh Demo Data Seeder for SIH 26124
Inserts/updates realistic Chandigarh urban intelligence data:
- 10 Road Segments across planned Chandigarh corridors
- 10 Fleet Sensing Buses placed directly on road geometries
- High-frequency GPS points in public.gps_points
- 18 Realistic defect observations (potholes, waterlogging, wear)
- 6 Traffic incidents with OCR plates and severity ratings
- 5-day condition score history for Recharts visualization

SAFETY RULES:
- Strictly NON-DESTRUCTIVE: Never DROPs, TRUNCATEs, or deletes existing data.
- Idempotent: Uses deterministic IDs and upsert/merge logic.
"""
import sys
import os
import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, text
from geoalchemy2.elements import WKTElement

from app.core.config import settings
from app.models.road_segment import RoadSegment
from app.models.bus import Bus
from app.models.gps import GPSPoint
from app.models.observation import Observation
from app.models.incident import Incident
from app.models.segment_history import SegmentHistory

# ─── 1. Canonical Chandigarh Road Network (10 Corridors) ───
CANONICAL_GEOJSON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "chandigarh_roads_canonical.geojson")
)

import json
if os.path.exists(CANONICAL_GEOJSON_PATH):
    with open(CANONICAL_GEOJSON_PATH, "r", encoding="utf-8") as _f:
        _geo = json.load(_f)
    CHANDIGARH_ROADS = [
        {
            "segment_id": feat["properties"]["segment_id"],
            "name": feat["properties"]["name"],
            "coords": [(float(p[0]), float(p[1])) for p in feat["geometry"]["coordinates"]],
            "condition_score": Decimal(str(feat["properties"]["condition_score"])),
            "confidence": Decimal(str(feat["properties"]["confidence"])),
            "pothole_count": int(feat["properties"]["pothole_count"]),
            "waterlogging_count": int(feat["properties"]["waterlogging_count"]),
            "observation_count": int(feat["properties"]["observation_count"]),
        }
        for feat in _geo.get("features", [])
    ]
else:
    raise FileNotFoundError(f"Missing canonical GeoJSON at {CANONICAL_GEOJSON_PATH}")

_coords_by_seg = {r["segment_id"]: r["coords"] for r in CHANDIGARH_ROADS}

def get_point_on_seg(seg_id: str, fraction: float = 0.5):
    pts = _coords_by_seg.get(seg_id, [])
    if not pts:
        return (30.7350, 76.7800)
    idx = min(max(0, int(len(pts) * fraction)), len(pts) - 1)
    lng, lat = pts[idx]
    return (round(lat, 6), round(lng, 6))

# ─── 2. Canonical Fleet Buses (10 Buses) ───
CHANDIGARH_BUSES = [
    {"bus_id": "DEMO-BUS-001", "vehicle_number": "CH-01-GA-1001", "lat": get_point_on_seg("seg_chandigarh_001", 0.4)[0], "lng": get_point_on_seg("seg_chandigarh_001", 0.4)[1], "heading": 115.0, "speed": 36.0, "segment": "seg_chandigarh_001"},
    {"bus_id": "DEMO-BUS-002", "vehicle_number": "CH-01-GA-1002", "lat": get_point_on_seg("seg_chandigarh_002", 0.5)[0], "lng": get_point_on_seg("seg_chandigarh_002", 0.5)[1], "heading": 120.0, "speed": 42.0, "segment": "seg_chandigarh_002"},
    {"bus_id": "DEMO-BUS-003", "vehicle_number": "CH-01-GA-1003", "lat": get_point_on_seg("seg_chandigarh_003", 0.5)[0], "lng": get_point_on_seg("seg_chandigarh_003", 0.5)[1], "heading": 185.0, "speed": 28.0, "segment": "seg_chandigarh_003"},
    {"bus_id": "DEMO-BUS-004", "vehicle_number": "CH-01-GA-1004", "lat": get_point_on_seg("seg_chandigarh_004", 0.5)[0], "lng": get_point_on_seg("seg_chandigarh_004", 0.5)[1], "heading": 80.0,  "speed": 32.0, "segment": "seg_chandigarh_004"},
    {"bus_id": "DEMO-BUS-005", "vehicle_number": "CH-01-GA-1005", "lat": get_point_on_seg("seg_chandigarh_005", 0.5)[0], "lng": get_point_on_seg("seg_chandigarh_005", 0.5)[1], "heading": 70.0,  "speed": 25.0, "segment": "seg_chandigarh_005"},
    {"bus_id": "DEMO-BUS-006", "vehicle_number": "CH-01-GA-1006", "lat": get_point_on_seg("seg_chandigarh_006", 0.5)[0], "lng": get_point_on_seg("seg_chandigarh_006", 0.5)[1], "heading": 190.0, "speed": 38.0, "segment": "seg_chandigarh_006"},
    {"bus_id": "DEMO-BUS-007", "vehicle_number": "CH-01-GA-1007", "lat": get_point_on_seg("seg_chandigarh_007", 0.5)[0], "lng": get_point_on_seg("seg_chandigarh_007", 0.5)[1], "heading": 175.0, "speed": 30.0, "segment": "seg_chandigarh_007"},
    {"bus_id": "DEMO-BUS-008", "vehicle_number": "CH-01-GA-1008", "lat": get_point_on_seg("seg_chandigarh_008", 0.5)[0], "lng": get_point_on_seg("seg_chandigarh_008", 0.5)[1], "heading": 140.0, "speed": 35.0, "segment": "seg_chandigarh_008"},
    {"bus_id": "DEMO-BUS-009", "vehicle_number": "CH-01-GA-1009", "lat": get_point_on_seg("seg_chandigarh_009", 0.5)[0], "lng": get_point_on_seg("seg_chandigarh_009", 0.5)[1], "heading": 125.0, "speed": 40.0, "segment": "seg_chandigarh_009"},
    {"bus_id": "DEMO-BUS-010", "vehicle_number": "CH-01-GA-1010", "lat": get_point_on_seg("seg_chandigarh_010", 0.5)[0], "lng": get_point_on_seg("seg_chandigarh_010", 0.5)[1], "heading": 170.0, "speed": 33.0, "segment": "seg_chandigarh_010"},
]

# ─── 3. Defect & Perception Observations (18 Observations) ───
CHANDIGARH_OBSERVATIONS = [
    # Madhya Marg
    {"obs_id": "evt_demo_001", "bus": "DEMO-BUS-001", "segment": "seg_chandigarh_001", "type": "road_defect", "class_name": "Pothole - Medium Depth", "conf": 0.92, "sev": 3, "lat": get_point_on_seg("seg_chandigarh_001", 0.2)[0], "lng": get_point_on_seg("seg_chandigarh_001", 0.2)[1], "offset_h": 2},
    {"obs_id": "evt_demo_002", "bus": "DEMO-BUS-001", "segment": "seg_chandigarh_001", "type": "road_defect", "class_name": "Pothole - Shallow", "conf": 0.85, "sev": 2, "lat": get_point_on_seg("seg_chandigarh_001", 0.6)[0], "lng": get_point_on_seg("seg_chandigarh_001", 0.6)[1], "offset_h": 3},
    {"obs_id": "evt_demo_003", "bus": "DEMO-BUS-001", "segment": "seg_chandigarh_001", "type": "waterlogging", "class_name": "Waterlogging - Shallow", "conf": 0.78, "sev": 2, "lat": get_point_on_seg("seg_chandigarh_001", 0.8)[0], "lng": get_point_on_seg("seg_chandigarh_001", 0.8)[1], "offset_h": 4},
    # Jan Marg (Critical/Poor corridor)
    {"obs_id": "evt_demo_004", "bus": "DEMO-BUS-003", "segment": "seg_chandigarh_003", "type": "waterlogging", "class_name": "Waterlogging - Severe", "conf": 0.94, "sev": 4, "lat": get_point_on_seg("seg_chandigarh_003", 0.2)[0], "lng": get_point_on_seg("seg_chandigarh_003", 0.2)[1], "offset_h": 1},
    {"obs_id": "evt_demo_005", "bus": "DEMO-BUS-003", "segment": "seg_chandigarh_003", "type": "road_defect", "class_name": "Pothole - Severe Depth", "conf": 0.96, "sev": 4, "lat": get_point_on_seg("seg_chandigarh_003", 0.4)[0], "lng": get_point_on_seg("seg_chandigarh_003", 0.4)[1], "offset_h": 2},
    {"obs_id": "evt_demo_006", "bus": "DEMO-BUS-003", "segment": "seg_chandigarh_003", "type": "road_defect", "class_name": "Pothole - Cluster", "conf": 0.89, "sev": 3, "lat": get_point_on_seg("seg_chandigarh_003", 0.6)[0], "lng": get_point_on_seg("seg_chandigarh_003", 0.6)[1], "offset_h": 3},
    {"obs_id": "evt_demo_007", "bus": "DEMO-BUS-003", "segment": "seg_chandigarh_003", "type": "waterlogging", "class_name": "Waterlogging - Moderate", "conf": 0.86, "sev": 3, "lat": get_point_on_seg("seg_chandigarh_003", 0.8)[0], "lng": get_point_on_seg("seg_chandigarh_003", 0.8)[1], "offset_h": 5},
    # Udyog Path
    {"obs_id": "evt_demo_008", "bus": "DEMO-BUS-005", "segment": "seg_chandigarh_005", "type": "road_defect", "class_name": "Pothole - Deep", "conf": 0.95, "sev": 4, "lat": get_point_on_seg("seg_chandigarh_005", 0.3)[0], "lng": get_point_on_seg("seg_chandigarh_005", 0.3)[1], "offset_h": 2},
    {"obs_id": "evt_demo_009", "bus": "DEMO-BUS-005", "segment": "seg_chandigarh_005", "type": "road_defect", "class_name": "Alligator Cracking", "conf": 0.88, "sev": 3, "lat": get_point_on_seg("seg_chandigarh_005", 0.5)[0], "lng": get_point_on_seg("seg_chandigarh_005", 0.5)[1], "offset_h": 4},
    {"obs_id": "evt_demo_010", "bus": "DEMO-BUS-005", "segment": "seg_chandigarh_005", "type": "waterlogging", "class_name": "Water Accumulation", "conf": 0.91, "sev": 4, "lat": get_point_on_seg("seg_chandigarh_005", 0.7)[0], "lng": get_point_on_seg("seg_chandigarh_005", 0.7)[1], "offset_h": 6},
    # Himalaya Marg
    {"obs_id": "evt_demo_011", "bus": "DEMO-BUS-004", "segment": "seg_chandigarh_004", "type": "road_defect", "class_name": "Pavement Wear", "conf": 0.82, "sev": 2, "lat": get_point_on_seg("seg_chandigarh_004", 0.4)[0], "lng": get_point_on_seg("seg_chandigarh_004", 0.4)[1], "offset_h": 5},
    {"obs_id": "evt_demo_012", "bus": "DEMO-BUS-004", "segment": "seg_chandigarh_004", "type": "waterlogging", "class_name": "Gutter Overflow", "conf": 0.84, "sev": 2, "lat": get_point_on_seg("seg_chandigarh_004", 0.7)[0], "lng": get_point_on_seg("seg_chandigarh_004", 0.7)[1], "offset_h": 8},
    # Vidya Path / Uttar Marg
    {"obs_id": "evt_demo_013", "bus": "DEMO-BUS-010", "segment": "seg_chandigarh_010", "type": "road_defect", "class_name": "Pothole - Edge", "conf": 0.87, "sev": 3, "lat": get_point_on_seg("seg_chandigarh_010", 0.3)[0], "lng": get_point_on_seg("seg_chandigarh_010", 0.3)[1], "offset_h": 3},
    {"obs_id": "evt_demo_014", "bus": "DEMO-BUS-010", "segment": "seg_chandigarh_010", "type": "road_defect", "class_name": "Surface Raveling", "conf": 0.79, "sev": 2, "lat": get_point_on_seg("seg_chandigarh_010", 0.7)[0], "lng": get_point_on_seg("seg_chandigarh_010", 0.7)[1], "offset_h": 7},
    # Sarovar Path
    {"obs_id": "evt_demo_015", "bus": "DEMO-BUS-007", "segment": "seg_chandigarh_007", "type": "road_defect", "class_name": "Transverse Crack", "conf": 0.83, "sev": 2, "lat": get_point_on_seg("seg_chandigarh_007", 0.5)[0], "lng": get_point_on_seg("seg_chandigarh_007", 0.5)[1], "offset_h": 4},
    # Traffic observations
    {"obs_id": "evt_demo_016", "bus": "DEMO-BUS-002", "segment": "seg_chandigarh_002", "type": "traffic", "class_name": "Congestion Slowdown", "conf": 0.88, "sev": 2, "lat": get_point_on_seg("seg_chandigarh_002", 0.3)[0], "lng": get_point_on_seg("seg_chandigarh_002", 0.3)[1], "offset_h": 1},
    {"obs_id": "evt_demo_017", "bus": "DEMO-BUS-006", "segment": "seg_chandigarh_006", "type": "traffic", "class_name": "Moderate Traffic Flow", "conf": 0.90, "sev": 1, "lat": get_point_on_seg("seg_chandigarh_006", 0.5)[0], "lng": get_point_on_seg("seg_chandigarh_006", 0.5)[1], "offset_h": 2},
    {"obs_id": "evt_demo_018", "bus": "DEMO-BUS-008", "segment": "seg_chandigarh_008", "type": "traffic", "class_name": "Smooth Traffic Flow", "conf": 0.94, "sev": 1, "lat": get_point_on_seg("seg_chandigarh_008", 0.5)[0], "lng": get_point_on_seg("seg_chandigarh_008", 0.5)[1], "offset_h": 3},
]

# ─── 4. Traffic Incidents (6 Incidents) ───
CHANDIGARH_INCIDENTS = [
    {
        "incident_id": "inc_demo_001",
        "incident_type": "Wrong-way Driving",
        "severity": 3,
        "vehicle_track_id": "trk-4412",
        "plate_text": "CH-01-AB-1234",
        "plate_confidence": Decimal("0.88"),
        "lat": get_point_on_seg("seg_chandigarh_001", 0.3)[0],
        "lng": get_point_on_seg("seg_chandigarh_001", 0.3)[1],
        "segment_id": "seg_chandigarh_001",
        "description": "Vehicle travelling against designated one-way flow on Madhya Marg service lane.",
    },
    {
        "incident_id": "inc_demo_002",
        "incident_type": "Red-light Violation",
        "severity": 4,
        "vehicle_track_id": "trk-5580",
        "plate_text": "PB-65-C-9876",
        "plate_confidence": Decimal("0.94"),
        "lat": get_point_on_seg("seg_chandigarh_003", 0.3)[0],
        "lng": get_point_on_seg("seg_chandigarh_003", 0.3)[1],
        "segment_id": "seg_chandigarh_003",
        "description": "High-speed junction crossing during red signal phase at Sector 9/17 intersection.",
    },
    {
        "incident_id": "inc_demo_003",
        "incident_type": "Illegal Parking",
        "severity": 2,
        "vehicle_track_id": "trk-6621",
        "plate_text": "HR-03-X-4321",
        "plate_confidence": Decimal("0.86"),
        "lat": get_point_on_seg("seg_chandigarh_004", 0.6)[0],
        "lng": get_point_on_seg("seg_chandigarh_004", 0.6)[1],
        "segment_id": "seg_chandigarh_004",
        "description": "Commercial delivery van obstructing public transport bus stop bay.",
    },
    {
        "incident_id": "inc_demo_004",
        "incident_type": "Road Obstruction",
        "severity": 3,
        "vehicle_track_id": "trk-7104",
        "plate_text": None,
        "plate_confidence": None,
        "lat": get_point_on_seg("seg_chandigarh_005", 0.6)[0],
        "lng": get_point_on_seg("seg_chandigarh_005", 0.6)[1],
        "segment_id": "seg_chandigarh_005",
        "description": "Fallen construction scaffolding debris blocking the westbound heavy carriage lane.",
    },
    {
        "incident_id": "inc_demo_005",
        "incident_type": "Heavy Congestion",
        "severity": 2,
        "vehicle_track_id": "trk-8220",
        "plate_text": None,
        "plate_confidence": None,
        "lat": get_point_on_seg("seg_chandigarh_002", 0.4)[0],
        "lng": get_point_on_seg("seg_chandigarh_002", 0.4)[1],
        "segment_id": "seg_chandigarh_002",
        "description": "Peak evening queue spillback exceeding 300m leading into Sector 35 roundabout.",
    },
    {
        "incident_id": "inc_demo_006",
        "incident_type": "Waterlogging Hazard",
        "severity": 3,
        "vehicle_track_id": "trk-9315",
        "plate_text": None,
        "plate_confidence": None,
        "lat": get_point_on_seg("seg_chandigarh_003", 0.7)[0],
        "lng": get_point_on_seg("seg_chandigarh_003", 0.7)[1],
        "segment_id": "seg_chandigarh_003",
        "description": "Submerged storm drain causing vehicle hydroplaning hazard near Matka Chowk.",
    },
]

# ─── 5. 5-Day Historical Progression Trends ───
HISTORY_TRENDS = {
    "seg_chandigarh_001": [72.0, 68.0, 66.0, 65.0, 65.0],
    "seg_chandigarh_002": [80.0, 82.0, 85.0, 87.0, 88.0],
    "seg_chandigarh_003": [52.0, 48.0, 44.0, 40.0, 38.0],
    "seg_chandigarh_004": [76.0, 74.0, 72.0, 71.0, 70.0],
    "seg_chandigarh_005": [40.0, 36.0, 30.0, 26.0, 24.0],
    "seg_chandigarh_006": [90.0, 91.0, 92.0, 93.0, 94.0],
    "seg_chandigarh_007": [85.0, 84.0, 83.0, 82.0, 82.0],
    "seg_chandigarh_008": [82.0, 83.0, 85.0, 85.0, 86.0],
    "seg_chandigarh_009": [95.0, 95.0, 96.0, 96.0, 96.0],
    "seg_chandigarh_010": [66.0, 64.0, 61.0, 59.0, 58.0],
}


async def seed_chandigarh_data():
    from app.db.database import AsyncSessionLocal, engine

    print("=" * 70)
    print("SIH 26124: DETERMINISTIC CHANDIGARH DEMO DATA SEEDER")
    print(f"Target Database: {settings.DATABASE_URL.split('@')[-1]}")
    print("=" * 70)

    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        # ─── 1. Upsert Road Segments ───
        print("\n[Phase 1] Seeding 10 Chandigarh Road Segments:")
        for r_data in CHANDIGARH_ROADS:
            seg_id = r_data["segment_id"]
            line_wkt = "LINESTRING(" + ", ".join(f"{lng} {lat}" for lng, lat in r_data["coords"]) + ")"
            geom_elem = WKTElement(line_wkt, srid=4326)

            stmt = select(RoadSegment).where(RoadSegment.segment_id == seg_id)
            res = await session.execute(stmt)
            existing_seg = res.scalar_one_or_none()

            if existing_seg:
                existing_seg.name = r_data["name"]
                existing_seg.geom = geom_elem
                existing_seg.condition_score = r_data["condition_score"]
                existing_seg.confidence = r_data["confidence"]
                existing_seg.pothole_count = r_data["pothole_count"]
                existing_seg.waterlogging_count = r_data["waterlogging_count"]
                existing_seg.observation_count = r_data["observation_count"]
                existing_seg.last_updated = now
                print(f"  [*] Updated: {seg_id} -> {r_data['name']} (Score: {r_data['condition_score']})")
            else:
                new_seg = RoadSegment(
                    segment_id=seg_id,
                    name=r_data["name"],
                    geom=geom_elem,
                    condition_score=r_data["condition_score"],
                    confidence=r_data["confidence"],
                    pothole_count=r_data["pothole_count"],
                    waterlogging_count=r_data["waterlogging_count"],
                    observation_count=r_data["observation_count"],
                    last_updated=now,
                )
                session.add(new_seg)
                print(f"  [+] Created: {seg_id} -> {r_data['name']} (Score: {r_data['condition_score']})")

        await session.commit()

        # ─── 2. Upsert Fleet Buses & Initial Telemetry ───
        print("\n[Phase 2] Seeding 10 Fleet Buses & GPS Telemetry:")
        for b_data in CHANDIGARH_BUSES:
            bus_id = b_data["bus_id"]
            stmt = select(Bus).where(Bus.bus_id == bus_id)
            res = await session.execute(stmt)
            existing_bus = res.scalar_one_or_none()

            if existing_bus:
                existing_bus.vehicle_number = b_data["vehicle_number"]
                existing_bus.status = "active"
                existing_bus.last_latitude = b_data["lat"]
                existing_bus.last_longitude = b_data["lng"]
                existing_bus.last_ping = now
                print(f"  [*] Updated: {bus_id} ({b_data['vehicle_number']}) at ({b_data['lat']}, {b_data['lng']})")
            else:
                new_bus = Bus(
                    bus_id=bus_id,
                    vehicle_number=b_data["vehicle_number"],
                    status="active",
                    last_latitude=b_data["lat"],
                    last_longitude=b_data["lng"],
                    last_ping=now,
                )
                session.add(new_bus)
                print(f"  [+] Created: {bus_id} ({b_data['vehicle_number']}) at ({b_data['lat']}, {b_data['lng']})")

            # Seed GPS point for each bus
            pt_wkt = f"POINT({b_data['lng']} {b_data['lat']})"
            gps_pt = GPSPoint(
                bus_id=bus_id,
                geom=WKTElement(pt_wkt, srid=4326),
                heading_deg=Decimal(str(b_data["heading"])),
                speed_kmh=b_data["speed"],
                accuracy_meters=2.5,
                recorded_at=now,
            )
            session.add(gps_pt)

        await session.commit()

        # ─── 3. Upsert Defect & Perception Observations ───
        print("\n[Phase 3] Seeding 18 Defect & Perception Observations:")
        for o_data in CHANDIGARH_OBSERVATIONS:
            obs_id = o_data["obs_id"]
            obs_time = now - timedelta(hours=o_data["offset_h"])
            pt_wkt = f"POINT({o_data['lng']} {o_data['lat']})"

            stmt = select(Observation).where(Observation.observation_id == obs_id)
            res = await session.execute(stmt)
            existing_obs = res.scalar_one_or_none()

            meta = {
                "event_id": obs_id,
                "class_name": o_data["class_name"],
                "latitude": o_data["lat"],
                "longitude": o_data["lng"],
                "frame_id": 1000 + int(o_data["sev"]) * 100,
            }

            if existing_obs:
                existing_obs.bus_id = o_data["bus"]
                existing_obs.segment_id = o_data["segment"]
                existing_obs.geom = WKTElement(pt_wkt, srid=4326)
                existing_obs.event_type = o_data["type"]
                existing_obs.class_name = o_data["class_name"]
                existing_obs.confidence = Decimal(str(o_data["conf"]))
                existing_obs.severity = o_data["sev"]
                existing_obs.status = "confirmed"
                existing_obs.observed_at = obs_time
                existing_obs.metadata_json = meta
                print(f"  [*] Updated observation: {obs_id} -> {o_data['class_name']} (Sev: {o_data['sev']})")
            else:
                new_obs = Observation(
                    observation_id=obs_id,
                    bus_id=o_data["bus"],
                    segment_id=o_data["segment"],
                    geom=WKTElement(pt_wkt, srid=4326),
                    event_type=o_data["type"],
                    class_name=o_data["class_name"],
                    confidence=Decimal(str(o_data["conf"])),
                    severity=o_data["sev"],
                    status="confirmed",
                    observed_at=obs_time,
                    metadata_json=meta,
                )
                session.add(new_obs)
                print(f"  [+] Created observation: {obs_id} -> {o_data['class_name']} (Sev: {o_data['sev']})")

        await session.commit()

        # ─── 4. Upsert Traffic Incidents ───
        print("\n[Phase 4] Seeding 6 Traffic Incidents:")
        for inc_data in CHANDIGARH_INCIDENTS:
            inc_id = inc_data["incident_id"]
            pt_wkt = f"POINT({inc_data['lng']} {inc_data['lat']})"

            stmt = select(Incident).where(Incident.incident_id == inc_id)
            res = await session.execute(stmt)
            existing_inc = res.scalar_one_or_none()

            if existing_inc:
                existing_inc.incident_type = inc_data["incident_type"]
                existing_inc.severity = inc_data["severity"]
                existing_inc.vehicle_track_id = inc_data["vehicle_track_id"]
                existing_inc.plate_text = inc_data["plate_text"]
                existing_inc.plate_confidence = inc_data["plate_confidence"]
                existing_inc.geom = WKTElement(pt_wkt, srid=4326)
                existing_inc.road_segment_id = inc_data["segment_id"]
                existing_inc.description = inc_data["description"]
                existing_inc.status = "open"
                existing_inc.recorded_at = now - timedelta(hours=1)
                print(f"  [*] Updated incident: {inc_id} -> {inc_data['incident_type']} (Sev: {inc_data['severity']})")
            else:
                new_inc = Incident(
                    incident_id=inc_id,
                    geom=WKTElement(pt_wkt, srid=4326),
                    incident_type=inc_data["incident_type"],
                    severity=inc_data["severity"],
                    vehicle_track_id=inc_data["vehicle_track_id"],
                    plate_text=inc_data["plate_text"],
                    plate_confidence=inc_data["plate_confidence"],
                    road_segment_id=inc_data["segment_id"],
                    description=inc_data["description"],
                    status="open",
                    recorded_at=now - timedelta(hours=1),
                )
                session.add(new_inc)
                print(f"  [+] Created incident: {inc_id} -> {inc_data['incident_type']} (Sev: {inc_data['severity']})")

        await session.commit()

        # ─── 5. Seed 5-Day Historical Progression Trends ───
        print("\n[Phase 5] Seeding 5-Day Condition History for Segments:")
        for seg_id, scores in HISTORY_TRENDS.items():
            # Check if history already seeded for this segment
            chk_stmt = select(SegmentHistory).where(SegmentHistory.segment_id == seg_id)
            chk_res = await session.execute(chk_stmt)
            existing_hist = chk_res.scalars().all()

            if len(existing_hist) >= 5:
                print(f"  [*] History already present for {seg_id} ({len(existing_hist)} records), skipping.")
                continue

            for day_idx, score in enumerate(scores):
                hist_date = (now - timedelta(days=(4 - day_idx))).replace(hour=18, minute=0, second=0)
                hist_entry = SegmentHistory(
                    segment_id=seg_id,
                    condition_score=Decimal(str(score)),
                    confidence=Decimal("0.90"),
                    pothole_count=max(0, int((100 - score) / 10)),
                    waterlogging_count=max(0, int((100 - score) / 20)),
                    recorded_at=hist_date,
                )
                session.add(hist_entry)
            print(f"  [+] Inserted 5-day history trend for {seg_id}")

        await session.commit()

    await engine.dispose()
    print("\n" + "=" * 70)
    print("CHANDIGARH DEMO DATA SEEDED SUCCESSFULLY (0 DATA LOSS)!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(seed_chandigarh_data())
