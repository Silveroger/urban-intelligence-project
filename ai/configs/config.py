"""
SIH 26124 — Edge AI Configuration & Detection Thresholds
Conforms to docs/AI_CONTRACT.md and docs/TECH_STACK.md
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ModelConfig:
    # Model weights path (falls back to lightweight YOLO or heuristic CV if weights not found)
    weights_path: str = "models/yolov8s.pt"
    device: str = "cpu"  # "cuda" if GPU is available else "cpu"
    inference_imgsz: int = 640
    conf_threshold: float = 0.40
    iou_threshold: float = 0.45


@dataclass
class EdgeConfig:
    bus_id: str = "BUS-101"
    sample_rate_fps: int = 5  # Process 5 frames per second to optimize edge compute
    evidence_dir: str = "backend/static/evidence"
    backend_ingest_url: str = "http://localhost:8000/api/v1/ingest/observation"
    backend_telemetry_url: str = "http://localhost:8000/api/v1/ingest/telemetry"
    
    # Class mappings & Severity configuration
    defect_classes: List[str] = field(default_factory=lambda: [
        "pothole",
        "damaged_road",
        "waterlogging",
        "missing_road_divider",
        "missing_zebra_crossing",
        "damaged_traffic_sign",
        "missing_traffic_sign"
    ])
    
    traffic_classes: List[str] = field(default_factory=lambda: [
        "car",
        "bus",
        "truck",
        "motorcycle",
        "auto_rickshaw"
    ])
    
    pedestrian_classes: List[str] = field(default_factory=lambda: [
        "pedestrian",
        "school_child",
        "vulnerable_pedestrian"
    ])
    
    # Severity weighting for road defects (1: Minor, 2: Moderate, 3: Severe, 4: Critical)
    severity_map: Dict[str, int] = field(default_factory=lambda: {
        "pothole": 3,
        "damaged_road": 2,
        "waterlogging": 3,
        "missing_road_divider": 3,
        "missing_zebra_crossing": 2,
        "damaged_traffic_sign": 2,
        "missing_traffic_sign": 3,
        "illegal_parking": 2,
        "rash_driving": 4,
        "hit_and_run": 4,
        "vulnerable_pedestrian": 3
    })
