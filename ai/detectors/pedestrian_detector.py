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

    def _ensure_model(self):
        """Lazily loads normal YOLO model with standard COCO classes (e.g. yolov8n.pt) if needed."""
        if self.model is not None:
            return self.model
        try:
            from pathlib import Path
            from ultralytics import YOLO
            from ai.configs.config import ModelConfig
            cfg = ModelConfig()
            for candidate in [cfg.normal_weights_path, "yolov8n.pt", "ai/models/yolo26n.pt", "models/yolo26n.pt", "yolo26n.pt"]:
                if candidate and Path(candidate).exists() and Path(candidate).stat().st_size > 1024:
                    self.model = YOLO(candidate)
                    break
        except Exception:
            pass
        return self.model

    def detect(self, frame: np.ndarray) -> List[Dict]:
        from ai.configs.config import EdgeConfig
        cfg = EdgeConfig()
        if not getattr(cfg, 'enable_pedestrian_detector', True):
            return []

        h, w = frame.shape[:2]
        detections: List[Dict] = []
        model = self._ensure_model()

        if model is not None:
            try:
                results = model(frame, conf=self.conf_thresh, verbose=False)
                for r in results:
                    for box in r.boxes:
                        cls_id = int(box.cls[0].item())
                        name = r.names.get(cls_id, "").lower()
                        conf = float(box.conf[0].item())
                        xyxy = [int(v) for v in box.xyxy[0].tolist()]

                        if "person" in name or "pedestrian" in name:
                            box_bottom = xyxy[3]
                            box_height = xyxy[3] - xyxy[1]
                            
                            # Check if person is on roadway (box bottom in lower 70% of frame)
                            is_in_roadway = box_bottom > int(h * 0.30)
                            is_child = box_height < int(h * 0.32)

                            if is_in_roadway:
                                detections.append({
                                    "class_name": "vulnerable_person",
                                    "confidence": round(conf, 2),
                                    "bbox": xyxy,
                                    "severity": 3 if is_child else 2
                                })
            except Exception:
                pass

        return detections

