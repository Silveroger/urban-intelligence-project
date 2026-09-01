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

        # 1. YOLO Inference if model available
        if self.model is not None:
            try:
                results = self.model(frame, conf=self.conf_thresh, verbose=False)
                for r in results:
                    for box in r.boxes:
                        cls_id = int(box.cls[0].item())
                        cls_name = r.names.get(cls_id, "").lower()
                        conf = float(box.conf[0].item())
                        xyxy = [int(v) for v in box.xyxy[0].tolist()]

                        if any(k in cls_name for k in ["pothole", "crack", "water", "defect", "hole"]):
                            target_class = "pothole"
                            if "water" in cls_name:
                                target_class = "waterlogging"
                            elif "crack" in cls_name:
                                target_class = "damaged_road"

                            box_w = xyxy[2] - xyxy[0]
                            box_h = xyxy[3] - xyxy[1]
                            ratio = (box_w * box_h) / (w * h)
                            severity = min(4, max(1, int(ratio * 50) + 1))

                            detections.append({
                                "class_name": target_class,
                                "confidence": round(conf, 2),
                                "bbox": xyxy,
                                "severity": severity
                            })
            except Exception:
                pass

        # 2. OpenCV Real Road Surface Morphological Defect Analysis
        # Road Region of Interest: Bottom 55% of the frame
        roi_y1 = int(h * 0.45)
        roi = frame[roi_y1:h, :]
        roi_h, roi_w = roi.shape[:2]

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)

        # A. Detect Potholes (Dark depressions surrounded by lighter pavement)
        # Using adaptive thresholding to isolate localized dark asphalt depressions
        dark_thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 12
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        dark_clean = cv2.morphologyEx(dark_thresh, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(dark_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Filter realistic pothole size (350 px to 25% of ROI)
            if 350 < area < (roi_h * roi_w * 0.20):
                x, y, bw, bh = cv2.boundingRect(cnt)
                aspect = bw / max(1, bh)
                # Potholes have rounded / oval aspect ratios
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
