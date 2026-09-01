"""
SIH 26124 — In-Memory Event, Incident & Telemetry Store
Provides persistence and aggregation queries for dashboard REST endpoints.
Conforms to docs/API_CONTRACT.md
"""

from typing import Dict, List, Optional
from backend.app.models.event import ObservationEvent
from backend.app.models.incident import Incident
from backend.app.models.telemetry import BusTelemetry


class ObservationStore:
    def __init__(self):
        self.events: List[Dict] = []
        self.incidents: List[Dict] = []
        self.buses: Dict[str, Dict] = {}
        self._seed_initial_data()

    def _seed_initial_data(self):
        # Seed realistic baseline observations matching docs/API_CONTRACT.md
        self.events = [
            {
                "event_id": "evt_pot_001",
                "bus_id": "BUS-102",
                "timestamp": "2026-08-31T15:20:10+05:30",
                "latitude": 30.7333,
                "longitude": 76.7794,
                "road_segment_id": "seg_chandigarh_001",
                "event_type": "road_defect",
                "class_name": "pothole",
                "confidence": 0.89,
                "severity": 3,
                "frame_id": 4120,
                "evidence_uri": "/evidence/evt_pot_001.jpg"
            },
            {
                "event_id": "evt_water_002",
                "bus_id": "BUS-103",
                "timestamp": "2026-08-31T15:45:00+05:30",
                "latitude": 30.7380,
                "longitude": 76.7850,
                "road_segment_id": "seg_chandigarh_002",
                "event_type": "waterlogging",
                "class_name": "waterlogging",
                "confidence": 0.92,
                "severity": 2,
                "frame_id": 4350,
                "evidence_uri": "/evidence/evt_water_002.jpg"
            },
            {
                "event_id": "evt_infra_003",
                "bus_id": "BUS-101",
                "timestamp": "2026-08-31T16:10:00+05:30",
                "latitude": 30.7250,
                "longitude": 76.7720,
                "road_segment_id": "seg_chandigarh_003",
                "event_type": "road_defect",
                "class_name": "missing_zebra_crossing",
                "confidence": 0.84,
                "severity": 2,
                "frame_id": 4600,
                "evidence_uri": "/evidence/evt_infra_003.jpg"
            }
        ]

        self.incidents = [
            {
                "incident_id": "inc_001",
                "timestamp": "2026-08-31T16:05:00+05:30",
                "latitude": 30.7350,
                "longitude": 76.7820,
                "incident_type": "illegal_parking",
                "severity": 2,
                "vehicle_track_id": "trk_901",
                "plate_text": "CH01AB1234",
                "plate_confidence": 0.94,
                "evidence_uri": "/evidence/inc_001.jpg"
            },
            {
                "incident_id": "inc_002",
                "timestamp": "2026-08-31T16:25:00+05:30",
                "latitude": 30.7220,
                "longitude": 76.7700,
                "incident_type": "rash_driving",
                "severity": 4,
                "vehicle_track_id": "trk_905",
                "plate_text": "PB65X8899",
                "plate_confidence": 0.91,
                "evidence_uri": "/evidence/inc_002.jpg"
            }
        ]

        self.buses = {
            "BUS-101": {
                "bus_id": "BUS-101",
                "latitude": 30.7345,
                "longitude": 76.7801,
                "heading_deg": 142.5,
                "speed_kmh": 32.0,
                "timestamp": "2026-08-31T16:15:00+05:30"
            },
            "BUS-102": {
                "bus_id": "BUS-102",
                "latitude": 30.7390,
                "longitude": 76.7860,
                "heading_deg": 90.0,
                "speed_kmh": 28.5,
                "timestamp": "2026-08-31T16:15:00+05:30"
            },
            "BUS-104": {
                "bus_id": "BUS-104",
                "latitude": 30.7270,
                "longitude": 76.7740,
                "heading_deg": 220.0,
                "speed_kmh": 35.0,
                "timestamp": "2026-08-31T16:15:00+05:30"
            }
        }

    def add_event(self, event_dict: Dict):
        self.events.insert(0, event_dict)
        if len(self.events) > 300:
            self.events.pop()

    def add_incident(self, incident_dict: Dict):
        self.incidents.insert(0, incident_dict)
        if len(self.incidents) > 100:
            self.incidents.pop()

    def update_telemetry(self, bus_id: str, telemetry_dict: Dict):
        self.buses[bus_id] = telemetry_dict

    def get_events(self, event_type: Optional[str] = None, min_severity: Optional[int] = None) -> List[Dict]:
        res = self.events
        if event_type:
            res = [e for e in res if e.get("event_type") == event_type]
        if min_severity:
            res = [e for e in res if (e.get("severity") or 1) >= min_severity]
        return res

    def get_incidents(self) -> List[Dict]:
        return self.incidents

    def get_buses(self) -> List[Dict]:
        return list(self.buses.values())


obs_store = ObservationStore()
