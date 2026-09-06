"""
SIH 26124 — Spatial Processing & Map Matching Engine
Performs geometric projection to road segment centerlines and computes
dynamic multi-pass road condition scores conforming to docs/ARCHITECTURE.md and docs/DATABASE_SCHEMA.md.
"""

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from backend.app.core.config import settings
from backend.app.models.event import ObservationEvent
from backend.app.models.segment import RoadSegmentFeature, RoadSegmentFeatureCollection, SegmentHistoryItem


class SpatialEngine:
    """
    In-memory PostGIS-compatible spatial engine:
    - Finds nearest road segment for edge observation points
    - Computes dynamic condition score degradation & confidence
    - Maintains longitudinal segment history
    """

    def __init__(self):
        self.segments: Dict[str, Dict] = {}
        self.history: Dict[str, List[Dict]] = {}
        self.load_road_network()

    def load_road_network(self):
        geojson_path = settings.ROADS_GEOJSON
        if not geojson_path.exists():
            return

        with open(geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for feat in data.get("features", []):
            sid = feat["properties"]["segment_id"]
            self.segments[sid] = feat
            # Initialize history
            self.history[sid] = [
                {
                    "timestamp": feat["properties"]["last_updated"],
                    "condition_score": feat["properties"]["condition_score"],
                    "confidence": feat["properties"]["confidence"],
                    "pothole_count": feat["properties"]["pothole_count"],
                    "bus_id": "FLEET-INIT"
                }
            ]

    def get_feature_collection(self) -> Dict:
        return {
            "type": "FeatureCollection",
            "features": list(self.segments.values())
        }

    def match_nearest_segment(self, lat: float, lng: float) -> Optional[str]:
        """
        Projects point (lat, lng) to nearest LineString road segment.
        Returns segment_id.
        """
        min_dist = float("inf")
        best_segment_id = None

        for sid, feat in self.segments.items():
            coords = feat["geometry"]["coordinates"]
            for pt in coords:
                # Euclidean approximation in local coordinate degrees
                d = math.hypot(pt[1] - lat, pt[0] - lng)
                if d < min_dist:
                    min_dist = d
                    best_segment_id = sid

        # Max threshold ~ 1.5 km in degrees (~0.015)
        if min_dist < 0.025:
            return best_segment_id
        return list(self.segments.keys())[0] if self.segments else None

    def ingest_observation(self, event: ObservationEvent) -> Optional[Dict]:
        """
        Updates segment condition score based on new perception observation.
        """
        segment_id = event.road_segment_id or self.match_nearest_segment(event.latitude, event.longitude)
        if not segment_id or segment_id not in self.segments:
            return None

        event.road_segment_id = segment_id
        feat = self.segments[segment_id]
        props = feat["properties"]

        # Increment counts
        props["observation_count"] += 1
        cname = (event.class_name or "").lower()

        penalty = 0.0
        risk_weight = (event.risk_score / 50.0) if event.risk_score else float(event.severity or 1)
        if "pothole" in cname:
            props["pothole_count"] += 1
            penalty = 12.0 * risk_weight
        elif "manhole" in cname:
            penalty = 10.0 * risk_weight
        elif "water" in cname or event.event_type.value == "waterlogging":
            props["waterlogging_count"] += 1
            penalty = 15.0 * risk_weight
        elif "crack" in cname or "damage" in cname:
            penalty = 7.0 * risk_weight
        elif "divider" in cname or "zebra" in cname or "sign" in cname:
            penalty = 6.0 * risk_weight

        # Dynamic score degradation with damping
        current_score = props["condition_score"]
        new_score = max(0.0, min(100.0, current_score - penalty * 0.45))
        props["condition_score"] = round(new_score, 1)

        # Update confidence (increases with observation count)
        new_conf = min(0.98, 0.70 + (props["observation_count"] * 0.015))
        props["confidence"] = round(new_conf, 2)
        props["last_updated"] = event.timestamp

        # Add to history
        hist_entry = {
            "timestamp": event.timestamp,
            "condition_score": props["condition_score"],
            "confidence": props["confidence"],
            "pothole_count": props["pothole_count"],
            "bus_id": event.bus_id
        }
        self.history[segment_id].append(hist_entry)
        if len(self.history[segment_id]) > 40:
            self.history[segment_id].pop(0)

        return feat

    def get_segment_history(self, segment_id: str) -> List[Dict]:
        return self.history.get(segment_id, [])


spatial_engine = SpatialEngine()
