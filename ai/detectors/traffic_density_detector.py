"""
SIH 26124 — Real-Time Traffic Density & Multi-Class Vehicle Detector
Runs YOLO model inference for vehicle classification (car, bus, truck, motorcycle, auto_rickshaw)
with exact bounding boxes, vehicle counts, and bottleneck alerts.
Conforms to docs/AI_CONTRACT.md
"""

from typing import Dict, List, Tuple
import numpy as np


class TrafficDensityDetector:
    def __init__(self, yolo_model=None, conf_thresh: float = 0.30):
        self.model = yolo_model
        self.conf_thresh = conf_thresh

    def detect(self, frame: np.ndarray) -> Dict:
        h, w = frame.shape[:2]
        detections: List[Dict] = []
        breakdown = {
            "car": 0,
            "bus": 0,
            "truck": 0,
            "motorcycle": 0,
            "auto_rickshaw": 0
        }

        try:
            import cv2
        except ImportError:
            return {
                "vehicle_count": 0,
                "density_score": 0.0,
                "is_bottleneck": False,
                "breakdown": breakdown,
                "detections": []
            }

        from ai.configs.config import EdgeConfig
        if not getattr(EdgeConfig, 'enable_traffic_detector', False):
            return {
                "vehicle_count": 0,
                "density_score": 0.0,
                "is_bottleneck": False,
                "breakdown": breakdown,
                "detections": []
            }

        # 1. YOLO Inference (only if traffic detection is enabled and model contains vehicle classes)
        if self.model is not None:
            try:
                results = self.model(frame, conf=self.conf_thresh, verbose=False)
                for r in results:
                    for box in r.boxes:
                        cls_id = int(box.cls[0].item())
                        name = r.names.get(cls_id, "").lower()
                        conf = float(box.conf[0].item())
                        xyxy = [int(v) for v in box.xyxy[0].tolist()]

                        mapped_class = None
                        if "car" in name:
                            mapped_class = "car"
                        elif "bus" in name:
                            mapped_class = "bus"
                        elif "truck" in name:
                            mapped_class = "truck"
                        elif "motorcycle" in name or "bicycle" in name:
                            mapped_class = "motorcycle"
                        elif "rickshaw" in name or "auto" in name:
                            mapped_class = "auto_rickshaw"

                        if mapped_class:
                            breakdown[mapped_class] = breakdown.get(mapped_class, 0) + 1
                            detections.append({
                                "class_name": mapped_class,
                                "confidence": round(conf, 2),
                                "bbox": xyxy
                            })
            except Exception:
                pass

        total_vehicles = len(detections)
        density_score = min(1.0, round(total_vehicles / 8.0, 2))
        is_bottleneck = total_vehicles >= 5 or density_score >= 0.60

        return {
            "vehicle_count": total_vehicles,
            "density_score": density_score,
            "is_bottleneck": is_bottleneck,
            "breakdown": breakdown,
            "detections": detections
        }
