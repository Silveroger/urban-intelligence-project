"""
SIH 26124 — Real-Time Vulnerable Pedestrian & Child Crossing Detector
Detects pedestrians in hazardous zones and school children crossings using YOLO model inference.
Conforms to docs/AI_CONTRACT.md
"""

from typing import Dict, List
import numpy as np


class PedestrianDetector:
    def __init__(self, yolo_model=None, conf_thresh: float = 0.35):
        self.model = yolo_model
        self.conf_thresh = conf_thresh

    def detect(self, frame: np.ndarray) -> List[Dict]:
        from ai.configs.config import EdgeConfig
        if not getattr(EdgeConfig, 'enable_pedestrian_detector', False):
            return []

        h, w = frame.shape[:2]
        detections: List[Dict] = []

        if self.model is not None:
            try:
                results = self.model(frame, conf=self.conf_thresh, verbose=False)
                for r in results:
                    for box in r.boxes:
                        cls_id = int(box.cls[0].item())
                        name = r.names.get(cls_id, "").lower()
                        conf = float(box.conf[0].item())
                        xyxy = [int(v) for v in box.xyxy[0].tolist()]

                        if "person" in name or "pedestrian" in name:
                            box_bottom = xyxy[3]
                            box_height = xyxy[3] - xyxy[1]
                            
                            # Check if person is in roadway (lower 60% of frame)
                            is_in_roadway = box_bottom > int(h * 0.45)
                            is_child = box_height < (h * 0.28)

                            if is_in_roadway:
                                target_class = "school_child" if is_child else "vulnerable_pedestrian"
                                detections.append({
                                    "class_name": target_class,
                                    "confidence": round(conf, 2),
                                    "bbox": xyxy,
                                    "severity": 3 if is_child else 2
                                })
            except Exception:
                pass

        return detections
