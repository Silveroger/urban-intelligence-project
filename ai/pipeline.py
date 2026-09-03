"""
SIH 26124 — Main Edge AI Computer Vision & Telemetry Pipeline
Processes bus video streams + GPS logs, runs OpenCV + YOLO detection,
displays real-time live detection window with HUD overlay, and transmits
structured metadata to the centralized urban intelligence platform.
Conforms to docs/AI_CONTRACT.md and docs/TECH_STACK.md
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional
import numpy as np

from ai.configs.config import EdgeConfig, ModelConfig
from ai.detectors.infrastructure_detector import InfrastructureDetector
from ai.detectors.pedestrian_detector import PedestrianDetector
from ai.detectors.plate_recognizer import PlateRecognizer
from ai.detectors.road_defect_detector import RoadDefectDetector
from ai.detectors.traffic_density_detector import TrafficDensityDetector
from ai.edge_optimizer import EdgeOptimizer
from ai.telemetry.gps_sync import GPSSync
from ai.tracker.vehicle_tracker import VehicleTracker


class EdgeAIPipeline:
    """
    End-to-end Edge Processing Engine for Fleet Buses:
    - Reads video stream / MP4 files from hardware team
    - Synchronizes frame indices with GPS coordinates & timestamps
    - Runs multi-model CV perception (Road defects, Traffic, Pedestrians, Incidents, OCR)
    - Displays real-time GUI window with bounding boxes & HUD telemetry
    - Emits structured JSON events to Backend Ingestion API & WebSockets
    """

    def __init__(
        self,
        bus_id: str = "BUS-101",
        weights_path: Optional[str] = None,
        backend_url: str = "http://localhost:8000"
    ):
        self.bus_id = bus_id
        self.backend_url = backend_url
        self.model = self._load_yolo(weights_path)

        # Initialize detector subsystems
        self.defect_detector = RoadDefectDetector(yolo_model=self.model)
        self.infra_detector = InfrastructureDetector(yolo_model=self.model)
        self.traffic_detector = TrafficDensityDetector(yolo_model=self.model)
        self.pedestrian_detector = PedestrianDetector(yolo_model=self.model)
        self.plate_recognizer = PlateRecognizer()
        self.tracker = VehicleTracker()
        self.optimizer = EdgeOptimizer(evidence_dir="backend/static/evidence")

    def _load_yolo(self, weights_path: Optional[str]):
        """
        Attempts to load YOLO weights if ultralytics is installed.
        Supports both .pt (PyTorch) and .onnx (ONNX Runtime) formats.
        Prioritizes YOLO 26n nano models (yolo26n.pt / yolo26n.onnx / yolov8n.pt) for edge inference.
        """
        try:
            from ultralytics import YOLO
            
            # Helper to check if file exists and has actual model weights
            def is_valid_weight_file(p: str) -> bool:
                path = Path(p)
                return path.exists() and path.is_file() and path.stat().st_size > 1024

            if weights_path and is_valid_weight_file(weights_path):
                print(f"[*] Loaded custom model weights from: {weights_path}")
                return YOLO(weights_path)
            
            cfg = ModelConfig()
            candidates = [
                cfg.weights_path,
                cfg.onnx_path,
                *cfg.candidate_weights,
                "models/road_defect_yolo26n.pt",
                "models/road_defect_yolo26n.onnx",
                "models/yolo26n.pt",
                "models/yolo26n.onnx"
            ]

            # Also scan models/ directory for any .pt or .onnx files
            for m_dir in ["models", "ai/models"]:
                if Path(m_dir).exists():
                    for f in Path(m_dir).glob("*.pt"):
                        candidates.append(str(f))
                    for f in Path(m_dir).glob("*.onnx"):
                        candidates.append(str(f))

            # Deduplicate while preserving order
            seen = set()
            ordered_candidates = []
            for c in candidates:
                if c not in seen:
                    seen.add(c)
                    ordered_candidates.append(c)

            for candidate in ordered_candidates:
                if is_valid_weight_file(candidate):
                    print(f"[*] Loaded YOLO model weights from: {candidate}")
                    return YOLO(candidate)
                    
            # Fallback to YOLO nano pretrained model
            if Path("yolov8n.pt").exists():
                return YOLO("yolov8n.pt")
            return YOLO("yolov8n.pt")
        except Exception as e:
            print(f"[!] Note: YOLO model initialization fallback ({e}). Using OpenCV vision pipeline.")
            return None

    # Default detector toggle map — Only road defects enabled until custom traffic model is trained
    DEFAULT_DETECTORS = {
        "road_defect": True,
        "waterlogging": True,
        "traffic": False,   # Disabled until custom traffic model is trained
        "incident": False,  # Disabled until custom traffic model is trained
    }

    def process_video(
        self,
        video_path: str,
        gps_path: Optional[str] = None,
        show_window: bool = True,
        delay_ms: int = 30,
        enabled_detectors: Optional[Dict[str, bool]] = None,
        on_event_callback: Optional[Callable[[Dict], None]] = None,
        on_telemetry_callback: Optional[Callable[[Dict], None]] = None,
        on_progress_callback: Optional[Callable[[float, int, int], None]] = None,
        output_annotated_path: Optional[str] = None
    ) -> Dict:
        """
        Processes a video file, RTSP stream, or hardware camera module (e.g. index 0, 1) with synchronized GPS data.
        If show_window is True, opens an interactive OpenCV window on your screen
        showing real-time bounding boxes, classifications, and telemetry HUD.

        enabled_detectors: dict mapping category keys to booleans.
            Keys: road_defect, waterlogging, traffic, incident
            If a key is False, the corresponding detector is skipped entirely.
        """
        try:
            import cv2
        except ImportError:
            raise RuntimeError("OpenCV (cv2) is required to process video streams.")

        # Detect if video_path is a hardware camera index (e.g. "0", "1", 0) or RTSP / file
        is_live_stream = False
        cap_source = video_path
        if isinstance(video_path, int) or (isinstance(video_path, str) and str(video_path).strip().isdigit()):
            cap_source = int(video_path)
            is_live_stream = True
        elif isinstance(video_path, str) and (video_path.startswith("rtsp://") or video_path.startswith("http://")):
            is_live_stream = True

        if is_live_stream and isinstance(cap_source, int):
            # Try DirectShow first on Windows for webcam stability, then standard
            cap = cv2.VideoCapture(cap_source, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(cap_source)
        else:
            cap = cv2.VideoCapture(cap_source)

        if not cap.isOpened():
            if is_live_stream and isinstance(cap_source, int):
                raise RuntimeError(
                    f"Hardware camera device index {cap_source} is not connected or accessible.\n"
                    f"-> If using your laptop webcam, try: python run_live_scanner.py --cam 0\n"
                    f"-> If running on a recorded video file, try: python run_live_scanner.py ai/sample_bus_camera.mp4"
                )
            raise FileNotFoundError(f"Cannot open video / camera source: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if not is_live_stream else 0
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        if fps <= 0 or fps > 120:
            fps = 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720

        # Resolve enabled detector categories (respecting EdgeConfig disablement flags)
        from ai.configs.config import EdgeConfig
        cfg = EdgeConfig()
        det_flags = {**self.DEFAULT_DETECTORS, **(enabled_detectors or {})}
        run_road_defect = det_flags.get("road_defect", True) and cfg.enable_road_defect_detector
        run_waterlogging = det_flags.get("waterlogging", True) and cfg.enable_waterlogging_detector
        run_traffic = det_flags.get("traffic", False) and cfg.enable_traffic_detector
        run_incident = det_flags.get("incident", False) and cfg.enable_incident_detector

        # Setup GPS Synchronizer
        gps_sync = GPSSync(fps=fps)
        if gps_path:
            if gps_path.endswith(".csv"):
                gps_sync.load_from_csv(gps_path)
            elif gps_path.endswith(".json"):
                gps_sync.load_from_json(gps_path)

        # Setup Video Writer if annotated output is requested
        writer = None
        if output_annotated_path:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(output_annotated_path, fourcc, fps, (width, height))

        events_generated: List[Dict] = []
        incidents_generated: List[Dict] = []
        telemetry_samples: List[Dict] = []

        frame_idx = 0
        step = max(1, int(fps / 10))  # Sample every few frames for detection

        window_name = f"SIH 26124 — Edge AI Live Perception Stream ({self.bus_id})"
        if show_window:
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 1024, 600)

        print(f"[*] Starting Edge AI Processing on '{video_path}' ({total_frames} frames @ {fps:.1f} FPS)...")
        if show_window:
            print("[*] Display window opened. Press 'q' or 'ESC' on the video window to stop.")

        current_boxes: List[Dict] = []
        alert_banner: Optional[str] = None
        alert_color = (0, 0, 255)

        while cap.isOpened():
            ret, raw_frame = cap.read()
            if not ret:
                break

            orig_h, orig_w = raw_frame.shape[:2]

            # Physical Road Surface Crop: Crops out sky/horizon & roadside clutter so only the road is visible
            if cfg.enable_road_roi_crop:
                crop_y1 = max(0, int(orig_h * cfg.roi_top_pct))
                crop_y2 = min(orig_h, int(orig_h * cfg.roi_bottom_pct))
                crop_x1 = max(0, int(orig_w * cfg.roi_left_pct))
                crop_x2 = min(orig_w, int(orig_w * cfg.roi_right_pct))
                frame = raw_frame[crop_y1:crop_y2, crop_x1:crop_x2]
            else:
                frame = raw_frame

            cur_h, cur_w = frame.shape[:2]
            display_frame = frame.copy()
            telemetry = gps_sync.get_telemetry_for_frame(frame_idx)

            # Process detection on sampled frames
            if frame_idx % step == 0:
                current_boxes = []
                alert_banner = None

                telemetry_payload = {
                    "bus_id": self.bus_id,
                    "latitude": telemetry["latitude"],
                    "longitude": telemetry["longitude"],
                    "heading_deg": telemetry["heading_deg"],
                    "speed_kmh": telemetry["speed_kmh"],
                    "timestamp": telemetry["timestamp"]
                }
                telemetry_samples.append(telemetry_payload)

                if on_telemetry_callback:
                    on_telemetry_callback(telemetry_payload)

                # 1. Road Defect & Hazard Detection
                if run_road_defect or run_waterlogging:
                    defects = self.defect_detector.detect(frame)
                    for d in defects:
                        is_water = "water" in d["class_name"]
                        # Skip if this specific category is disabled
                        if is_water and not run_waterlogging:
                            continue
                        if not is_water and not run_road_defect:
                            continue

                        current_boxes.append({
                            "bbox": d["bbox"],
                            "label": f"{d['class_name'].upper()} (SEV {d['severity']}) - {int(d['confidence']*100)}%",
                            "color": (0, 0, 255) if d["class_name"] == "pothole" else (255, 180, 0)
                        })
                        alert_banner = f"DEFECT DETECTED: {d['class_name'].upper()}"
                        alert_color = (0, 0, 255)

                        evt = self.optimizer.package_observation(
                            bus_id=self.bus_id,
                            telemetry=telemetry,
                            class_name=d["class_name"],
                            confidence=d["confidence"],
                            severity=d["severity"],
                            frame=frame,
                            bbox=d["bbox"],
                            frame_id=frame_idx,
                            event_type="waterlogging" if is_water else "road_defect"
                        )
                        if evt:
                            events_generated.append(evt)
                            if on_event_callback:
                                on_event_callback({"type": "NEW_EVENT", "payload": evt})

                # 2. Infrastructure Deficiencies (Zebra, Dividers, Signs)
                if run_road_defect:
                    infra = self.infra_detector.detect(frame)
                    for inf in infra:
                        current_boxes.append({
                            "bbox": inf["bbox"],
                            "label": f"GAP: {inf['class_name'].replace('_', ' ').upper()}",
                            "color": (255, 0, 255)
                        })
                        evt = self.optimizer.package_observation(
                            bus_id=self.bus_id,
                            telemetry=telemetry,
                            class_name=inf["class_name"],
                            confidence=inf["confidence"],
                            severity=inf["severity"],
                            frame=frame,
                            bbox=inf["bbox"],
                            frame_id=frame_idx,
                            event_type="road_defect"
                        )
                        if evt:
                            events_generated.append(evt)
                            if on_event_callback:
                                on_event_callback({"type": "NEW_EVENT", "payload": evt})

                # 3. Traffic Density & Vehicles
                traffic_info = {"vehicle_count": 0, "density_score": 0, "is_bottleneck": False, "breakdown": {}, "detections": []}
                if run_traffic:
                    traffic_info = self.traffic_detector.detect(frame)
                    for det in traffic_info["detections"]:
                        current_boxes.append({
                            "bbox": det["bbox"],
                            "label": f"{det['class_name']} ({int(det['confidence']*100)}%)",
                            "color": (0, 255, 100)
                        })

                    if traffic_info["is_bottleneck"]:
                        alert_banner = f"TRAFFIC CONGESTION (Density: {int(traffic_info['density_score']*100)}%)"
                        alert_color = (0, 165, 255)
                        evt = self.optimizer.package_observation(
                            bus_id=self.bus_id,
                            telemetry=telemetry,
                            class_name="congestion_cluster",
                            confidence=0.88,
                            severity=2,
                            frame=frame,
                            bbox=[0, 0, width, height],
                            frame_id=frame_idx,
                            event_type="traffic"
                        )
                        if evt:
                            events_generated.append(evt)
                            if on_event_callback:
                                on_event_callback({"type": "NEW_EVENT", "payload": evt})

                # 4. Vulnerable Pedestrian Situations
                if run_traffic:
                    pedestrians = self.pedestrian_detector.detect(frame)
                    for ped in pedestrians:
                        current_boxes.append({
                            "bbox": ped["bbox"],
                            "label": f"CAUTION: {ped['class_name'].upper()}",
                            "color": (0, 128, 255)
                        })
                        alert_banner = f"PEDESTRIAN SAFETY ALERT: {ped['class_name'].upper()}"
                        alert_color = (0, 140, 255)

                        evt = self.optimizer.package_observation(
                            bus_id=self.bus_id,
                            telemetry=telemetry,
                            class_name=ped["class_name"],
                            confidence=ped["confidence"],
                            severity=ped["severity"],
                            frame=frame,
                            bbox=ped["bbox"],
                            frame_id=frame_idx,
                            event_type="traffic"
                        )
                        if evt:
                            events_generated.append(evt)
                            if on_event_callback:
                                on_event_callback({"type": "NEW_EVENT", "payload": evt})

                # 5. Vehicle Tracking & Incidents
                if run_incident:
                    tracked_vehicles = self.tracker.update(traffic_info["detections"], frame_idx)
                    for trk in tracked_vehicles:
                        if trk.is_offending and not trk.plate_info:
                            last_bbox = trk.bbox_history[-1][1]
                            x1, y1, x2, y2 = last_bbox
                            veh_crop = frame[max(0, y1):min(height, y2), max(0, x1):min(width, x2)]
                            plate_res = self.plate_recognizer.recognize(veh_crop)
                            trk.plate_info = plate_res

                            plate_str = plate_res['plate_text'] if plate_res else 'UNKNOWN'
                            current_boxes.append({
                                "bbox": last_bbox,
                                "label": f"OFFENDER: {plate_str} ({int((plate_res['plate_confidence'] if plate_res else 0.5)*100)}%)",
                                "color": (0, 0, 255)
                            })
                            alert_banner = f"INCIDENT: RASH DRIVING ({plate_str})"
                            alert_color = (0, 0, 255)

                            inc_payload = self.optimizer.package_incident(
                                telemetry=telemetry,
                                incident_type=trk.incident_type or "rash_driving",
                                severity=4,
                                track_id=trk.track_id,
                                plate_text=plate_str,
                                plate_confidence=plate_res["plate_confidence"] if plate_res else 0.50,
                                frame=frame,
                                bbox=last_bbox,
                                frame_id=frame_idx
                            )
                            incidents_generated.append(inc_payload)
                            if on_event_callback:
                                on_event_callback({"type": "NEW_INCIDENT", "payload": inc_payload})

            # Draw Detections & Bounding Boxes (Potholes, Cracks, Manholes on Road Surface)
            for box_data in current_boxes:
                bx1, by1, bx2, by2 = box_data["bbox"]
                bcol = box_data["color"]
                lbl = box_data["label"]

                cv2.rectangle(display_frame, (bx1, by1), (bx2, by2), bcol, 2)
                # Label badge
                (tw, th), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                cv2.rectangle(display_frame, (bx1, max(0, by1 - 20)), (bx1 + tw + 6, max(20, by1)), bcol, -1)
                cv2.putText(
                    display_frame,
                    lbl,
                    (bx1 + 3, max(15, by1 - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (0, 0, 0) if sum(bcol) > 400 else (255, 255, 255),
                    1,
                    cv2.LINE_AA
                )

            # Draw Top HUD Telemetry Bar
            cv2.rectangle(display_frame, (0, 0), (cur_w, 42), (20, 20, 20), -1)
            hud_text1 = f"FLEET: {self.bus_id} | FRAME: {frame_idx}/{total_frames} ({int(frame_idx/max(1,total_frames)*100)}%) | SPEED: {telemetry['speed_kmh']} km/h"
            hud_text2 = f"GPS: {telemetry['latitude']:.5f} N, {telemetry['longitude']:.5f} E | HDG: {telemetry['heading_deg']} deg | ROAD CROPPED INFERENCE"
            cv2.putText(display_frame, hud_text1, (10, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 200), 1, cv2.LINE_AA)
            cv2.putText(display_frame, hud_text2, (10, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (220, 220, 220), 1, cv2.LINE_AA)

            # Draw Live Alert Banner if active
            if alert_banner:
                cv2.rectangle(display_frame, (0, cur_h - 36), (cur_w, cur_h), alert_color, -1)
                cv2.putText(
                    display_frame,
                    f"! ALERT: {alert_banner} !",
                    (int(cur_w * 0.15), cur_h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA
                )

            if writer:
                writer.write(display_frame)

            # Show Interactive GUI Window on Laptop Screen
            if show_window:
                cv2.imshow(window_name, display_frame)
                key = cv2.waitKey(max(1, delay_ms)) & 0xFF
                if key == ord('q') or key == 27:  # 'q' or ESC to exit
                    print("[!] User pressed exit in video window.")
                    break

            frame_idx += 1
            if on_progress_callback and total_frames > 0:
                progress = min(1.0, frame_idx / total_frames)
                on_progress_callback(progress, frame_idx, total_frames)

        cap.release()
        if writer:
            writer.release()
        if show_window:
            cv2.destroyAllWindows()

        summary = {
            "bus_id": self.bus_id,
            "total_frames_analyzed": frame_idx,
            "total_events_detected": len(events_generated),
            "total_incidents_flagged": len(incidents_generated),
            "events": events_generated,
            "incidents": incidents_generated,
            "telemetry_points": len(telemetry_samples)
        }

        print(f"[OK] Completed analysis: {len(events_generated)} events, {len(incidents_generated)} incidents.")
        return summary


if __name__ == "__main__":
    v_path = sys.argv[1] if len(sys.argv) > 1 else "ai/sample_bus_camera.mp4"
    g_path = sys.argv[2] if len(sys.argv) > 2 else "ai/sample_gps_track.json"
    
    if not Path(v_path).exists():
        from ai.test_video_generator import generate_synthetic_bus_run
        generate_synthetic_bus_run()

    pipeline = EdgeAIPipeline()
    res = pipeline.process_video(v_path, g_path, show_window=True, delay_ms=30)
    print(f"\n[Summary] Analyzed {res['total_frames_analyzed']} frames. Generated {res['total_events_detected']} events & {res['total_incidents_flagged']} incidents.")
