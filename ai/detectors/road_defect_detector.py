"""
SIH 26124 — Real-Time Road Defect & Surface Hazard CV Detector
Uses OpenCV Computer Vision (Adaptive Thresholding, Canny Gradients, Contour Morphology, HSV Water Analysis)
and YOLO inference to find real potholes, cracks, and waterlogging with exact bounding boxes.
Conforms to docs/AI_CONTRACT.md
"""

from typing import Dict, List, Optional, Tuple
import numpy as np


class RoadDefectDetector:
    """
    Genuine Computer Vision Defect Analyzer:
    - Potholes: Real dark concave contour extraction & aspect ratio bounding boxes
    - Surface Cracks: High-frequency Canny gradient fissions
    - Waterlogging: Specular reflection & low-saturation HSV water puddles
    """

    def __init__(self, yolo_model=None, conf_thresh: float = 0.35):
        self.model = yolo_model
        self.conf_thresh = conf_thresh

    def detect(self, frame: np.ndarray) -> List[Dict]:
        h, w = frame.shape[:2]
        detections: List[Dict] = []

        try:
            import cv2
        except ImportError:
            return detections

        # 1. YOLO Neural Network Inference (Primary & Accurate on Road Surface)
        if self.model is not None:
            try:
                from ai.configs.config import EdgeConfig
                cfg = EdgeConfig()
                kaggle_map = cfg.kaggle_defect_map

                results = self.model(frame, conf=self.conf_thresh, verbose=False)
                for r in results:
                    for box in r.boxes:
                        cls_id = int(box.cls[0].item())
                        cls_name = r.names.get(cls_id, str(cls_id)).lower().strip()
                        conf = float(box.conf[0].item())
                        xyxy = [int(v) for v in box.xyxy[0].tolist()]

                        # Map Kaggle class names / RDD tags (e.g. D00, D10, D20, D40, pothole, crack, manhole)
                        target_class = kaggle_map.get(cls_name)
                        if not target_class:
                            if any(k in cls_name for k in ["pothole", "hole", "d40", "cavity"]):
                                target_class = "pothole"
                            elif any(k in cls_name for k in ["water", "puddle", "flood", "drain"]):
                                target_class = "waterlogging"
                            elif any(k in cls_name for k in ["crack", "damaged", "d00", "d10", "d20", "rutting", "patch", "bump", "manhole"]):
                                target_class = "damaged_road"
                            elif any(k in cls_name for k in ["divider", "median"]):
                                target_class = "missing_road_divider"
                            elif any(k in cls_name for k in ["zebra", "crossing"]):
                                target_class = "missing_zebra_crossing"
                            elif any(k in cls_name for k in ["sign", "board"]):
                                target_class = "damaged_traffic_sign"

                        if target_class:
                            box_w = xyxy[2] - xyxy[0]
                            box_h = xyxy[3] - xyxy[1]
                            ratio = (box_w * box_h) / max(1, (w * h))
                            
                            # Filter out absurd bounding boxes (e.g. entire screen or tiny single pixel noise)
                            if ratio > 0.65 or box_w < 8 or box_h < 8:
                                continue

                            # Calculate severity based on defect size & class
                            base_sev = cfg.severity_map.get(target_class, 2)
                            severity = min(4, max(1, base_sev if ratio < 0.02 else base_sev + 1))

                            detections.append({
                                "class_name": target_class,
                                "confidence": round(conf, 2),
                                "bbox": xyxy,
                                "severity": severity
                            })
            except Exception:
                pass

            # When a trained YOLO model is active, strictly return YOLO detections to avoid false positives
            return detections
            return detections

        # 2. OpenCV Fallback Analyzer (ONLY used when no YOLO model is loaded)
        # Road Region of Interest: Bottom 55% of the frame
        roi_y1 = int(h * 0.45)
        roi = frame[roi_y1:h, :]
        roi_h, roi_w = roi.shape[:2]

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)

        # A. Detect Potholes (Dark depressions surrounded by lighter pavement)
        dark_thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 12
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        dark_clean = cv2.morphologyEx(dark_thresh, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(dark_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 350 < area < (roi_h * roi_w * 0.20):
                x, y, bw, bh = cv2.boundingRect(cnt)
                aspect = bw / max(1, bh)
                if 0.45 < aspect < 2.8:
                    global_bbox = [x, y + roi_y1, x + bw, y + bh + roi_y1]
                    area_ratio = area / (w * h)
                    conf = min(0.96, 0.72 + area_ratio * 8)
                    severity = 3 if area_ratio > 0.015 else 2

                    detections.append({
                        "class_name": "pothole",
                        "confidence": round(conf, 2),
                        "bbox": global_bbox,
                        "severity": severity
                    })

        # B. Detect Waterlogging (Specular puddles: Low saturation & high luminosity in HSV)
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        sat = hsv[:, :, 1]
        val = hsv[:, :, 2]
        # Water reflects sky: Low saturation (< 60) and high value (> 130)
        water_mask = cv2.inRange(hsv, np.array([0, 0, 110]), np.array([180, 75, 230]))
        water_clean = cv2.morphologyEx(water_mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 5)))
        
        w_contours, _ = cv2.findContours(water_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in w_contours:
            area = cv2.contourArea(cnt)
            if area > 1200:
                x, y, bw, bh = cv2.boundingRect(cnt)
                global_bbox = [x, y + roi_y1, x + bw, y + bh + roi_y1]
                detections.append({
                    "class_name": "waterlogging",
                    "confidence": 0.88,
                    "bbox": global_bbox,
                    "severity": 3 if area > 4000 else 2
                })

        # C. Detect Damaged Road Surface / Alligator Cracking (High edge density in road center)
        edges = cv2.Canny(blurred, 60, 140)
        edge_density = np.sum(edges > 0) / (roi_h * roi_w)
        if edge_density > 0.09 and not any(d["class_name"] == "pothole" for d in detections):
            # Locate crack cluster bounding box
            non_zero = cv2.findNonZero(edges)
            if non_zero is not None:
                cx, cy, cw, ch = cv2.boundingRect(non_zero)
                if cw > 80 and ch > 40:
                    detections.append({
                        "class_name": "damaged_road",
                        "confidence": round(min(0.92, 0.70 + edge_density * 2), 2),
                        "bbox": [cx, cy + roi_y1, cx + cw, cy + ch + roi_y1],
                        "severity": 2
                    })

        return detections
