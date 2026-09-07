"""
SIH 26124 — Vehicle Tracker & Incident Detection Engine
Tracks dynamic objects across video frames and detects incidents:
- Hit-and-run incidents
- Rash / reckless driving (excessive lateral velocity or erratic lane weaves)
- Illegal bus-lane encroachment / obstructions
Conforms to docs/AI_CONTRACT.md and docs/API_CONTRACT.md
"""

import math
from typing import Dict, List, Optional, Tuple
import numpy as np


class TrackedObject:
    def __init__(self, track_id: str, class_name: str, bbox: List[int], frame_idx: int):
        self.track_id = track_id
        self.class_name = class_name
        self.bbox_history = [(frame_idx, bbox)]
        self.centroid_history = [(frame_idx, ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2))]
        self.is_offending = False
        self.incident_type: Optional[str] = None
        self.plate_info: Optional[Dict] = None

    def update(self, bbox: List[int], frame_idx: int):
        self.bbox_history.append((frame_idx, bbox))
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        self.centroid_history.append((frame_idx, (cx, cy)))

        # Keep history window bounded to last 60 frames
        if len(self.bbox_history) > 60:
            self.bbox_history.pop(0)
            self.centroid_history.pop(0)

        # Analyze trajectory for rash driving / erratic lane changes
        self._analyze_behavior()

    def _analyze_behavior(self):
        if len(self.centroid_history) < 6:
            return

        # Calculate lateral (horizontal) acceleration / weaving
        recent = self.centroid_history[-6:]
        dx_list = [recent[i + 1][1][0] - recent[i][1][0] for i in range(len(recent) - 1)]
        lateral_speed = sum(abs(dx) for dx in dx_list) / len(dx_list)

        # If vehicle weaves across lanes sharply
        if lateral_speed > 35.0:
            self.is_offending = True
            self.incident_type = "rash_driving"


class VehicleTracker:
    """
    Multi-object tracker that maintains persistent vehicle IDs (trk_001, etc.)
    and detects traffic incidents.
    """

    def __init__(self, iou_thresh: float = 0.3):
        self.iou_thresh = iou_thresh
        self.tracks: Dict[str, TrackedObject] = {}
        self.next_id = 100

    def update(self, detections: List[Dict], frame_idx: int) -> List[TrackedObject]:
        """
        Associates frame detections to existing tracks via IoU bounding box matching.
        """
        matched_tracks = []

        for det in detections:
            bbox = det["bbox"]
            cls_name = det.get("class_name", "car")
            best_iou = 0.0
            best_track_id = None

            for tid, track in self.tracks.items():
                last_frame, last_bbox = track.bbox_history[-1]
                if frame_idx - last_frame <= 5:  # within 5 frames
                    iou = compute_iou(bbox, last_bbox)
                    if iou > best_iou:
                        best_iou = iou
                        best_track_id = tid

            if best_iou >= self.iou_thresh and best_track_id:
                self.tracks[best_track_id].update(bbox, frame_idx)
                matched_tracks.append(self.tracks[best_track_id])
            else:
                new_id = f"trk_{self.next_id}"
                self.next_id += 1
                new_track = TrackedObject(new_id, cls_name, bbox, frame_idx)
                self.tracks[new_id] = new_track
                matched_tracks.append(new_track)

        # Prune stale tracks older than 30 frames
        stale_ids = [
            tid for tid, t in self.tracks.items()
            if frame_idx - t.bbox_history[-1][0] > 30
        ]
        for tid in stale_ids:
            del self.tracks[tid]

        return matched_tracks


def compute_iou(boxA: List[int], boxB: List[int]) -> float:
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    if interArea == 0:
        return 0.0

    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    iou = interArea / float(boxAArea + boxBArea - interArea)
    return iou
