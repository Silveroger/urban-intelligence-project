"""
SIH 26124 — Edge AI Configuration & Detection Thresholds
Conforms to docs/AI_CONTRACT.md and docs/TECH_STACK.md
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ModelConfig:
    # Model weights path (supports YOLO 26n / custom Kaggle weights in .pt or .onnx formats)
    weights_path: str = "models/road_defect_yolo26n.pt"
    onnx_path: str = "models/road_defect_yolo26n.onnx"
    normal_weights_path: str = "yolov8n.pt"
    candidate_weights: List[str] = field(default_factory=lambda: [
        "models/road_defect_yolo26n.pt",
        "models/road_defect_yolo26n.onnx",
        "models/yolo26n.pt",
        "models/yolo26n.onnx",
        "ai/models/road_defect_yolo26n.pt",
        "ai/models/road_defect_yolo26n.onnx",
        "ai/models/yolo26n.pt",
        "ai/models/yolo26n.onnx",
        "yolo26n.pt",
        "yolo26n.onnx",
        "yolov8n.pt"
    ])
    device: str = "cpu"  # "cuda" if GPU is available else "cpu"
    inference_imgsz: int = 640
    conf_threshold: float = 0.35
    iou_threshold: float = 0.45


@dataclass
class EdgeConfig:
    bus_id: str = "BUS-101"
    sample_rate_fps: int = 5  # Process 5 frames per second to optimize edge compute
    camera_source: str = "0"   # Hardware SBC camera index ("0", "1", "2") or RTSP/HTTP URL or file path
    evidence_dir: str = "backend/static/evidence"
    backend_ingest_url: str = "http://localhost:8000/api/v1/ingest/observation"
    backend_telemetry_url: str = "http://localhost:8000/api/v1/ingest/telemetry"
    
    # Road Region of Interest (ROI) Cropping configuration
    # Crops away the sky, horizon, buildings, and side trees/sidewalks so only the road is visible
    enable_road_roi_crop: bool = True
    roi_top_pct: float = 0.40      # Cuts off top 40% (sky, horizon, overhead buildings)
    roi_bottom_pct: float = 0.96   # Cuts off bottom 4% (vehicle hood / camera mount)
    roi_left_pct: float = 0.12     # Cuts off left 12% (sidewalk / roadside clutter)
    roi_right_pct: float = 0.88    # Cuts off right 12% (sidewalk / roadside clutter)

    # Detector enablement flags (Road defects and vulnerable pedestrians enabled)
    enable_road_defect_detector: bool = True
    enable_waterlogging_detector: bool = True
    enable_traffic_detector: bool = False
    enable_incident_detector: bool = False
    enable_pedestrian_detector: bool = True
    
    # Class mappings & Severity configuration
    defect_classes: List[str] = field(default_factory=lambda: [
        "pothole",
        "manhole",
        "damaged_road",
        "waterlogging",
        "missing_road_divider",
        "missing_zebra_crossing",
        "damaged_traffic_sign",
        "missing_traffic_sign"
    ])

    # Kaggle dataset class tag alias mapping (e.g. RDD2020 / RDD2022 / Roboflow tags -> standard classes)
    kaggle_defect_map: Dict[str, str] = field(default_factory=lambda: {
        # Potholes
        "pothole": "pothole",
        "potholes": "pothole",
        "d40": "pothole",
        "pothole_cluster": "pothole",
        
        # Manholes
        "manhole": "manhole",
        "manholes": "manhole",
        "sunken_manhole": "manhole",
        "open_manhole": "manhole",
        "drain_cover": "manhole",

        # Cracks & Damaged Surface
        "crack": "damaged_road",
        "cracks": "damaged_road",
        "d00": "damaged_road",          # Longitudinal crack
        "d10": "damaged_road",          # Transverse crack
        "d20": "damaged_road",          # Alligator / Mesh crack
        "alligator_crack": "damaged_road",
        "longitudinal_crack": "damaged_road",
        "transverse_crack": "damaged_road",
        "damaged_road": "damaged_road",
        "damaged_pavement": "damaged_road",
        "rutting": "damaged_road",
        "raveling": "damaged_road",
        "bump": "damaged_road",
        "patch": "damaged_road",
        "patched_pothole": "damaged_road",

        # Waterlogging & Hazards
        "waterlogging": "waterlogging",
        "water": "waterlogging",
        "puddle": "waterlogging",
        "flooding": "waterlogging",
        "standing_water": "waterlogging",

        # Infrastructure
        "missing_divider": "missing_road_divider",
        "missing_road_divider": "missing_road_divider",
        "no_divider": "missing_road_divider",
        "missing_zebra": "missing_zebra_crossing",
        "missing_zebra_crossing": "missing_zebra_crossing",
        "faded_zebra_crossing": "missing_zebra_crossing",
        "damaged_sign": "damaged_traffic_sign",
        "damaged_traffic_sign": "damaged_traffic_sign",
        "missing_sign": "missing_traffic_sign",
        "missing_traffic_sign": "missing_traffic_sign"
    })
    
    traffic_classes: List[str] = field(default_factory=lambda: [
        "car",
        "bus",
        "truck",
        "motorcycle",
        "auto_rickshaw"
    ])
    
    pedestrian_classes: List[str] = field(default_factory=lambda: [
        "vulnerable_person",
        "pedestrian",
        "school_child",
        "vulnerable_pedestrian"
    ])
    
    # Severity weighting for road defects (1: Minor, 2: Moderate, 3: Severe, 4: Critical)
    severity_map: Dict[str, int] = field(default_factory=lambda: {
        "pothole": 3,
        "manhole": 3,
        "damaged_road": 2,
        "waterlogging": 3,
        "missing_road_divider": 3,
        "missing_zebra_crossing": 2,
        "damaged_traffic_sign": 2,
        "missing_traffic_sign": 3,
        "illegal_parking": 2,
        "rash_driving": 4,
        "hit_and_run": 4,
        "vulnerable_pedestrian": 3,
        "vulnerable_person": 3
    })
