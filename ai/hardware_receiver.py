"""
SIH 26124 — Smart Bus Hardware Receiver & Urban Intelligence Ingestion Node
Interfaces directly with the Raspberry Pi on-board bus hardware:
- Ingests video stream from Pi via PyAV (TCP Port 5000)
- Ingests GPS telemetry & video synchronization from Pi (TCP Port 5001)
- Performs frame-to-GPS temporal interpolation
- Runs YOLO 26n perception engine with breadth, depth, and risk factor scoring
- Saves local observations to observations.jsonl
- Returns real-time detections to Raspberry Pi on Port 5002
- Simultaneously forwards observations & telemetry to Centralized Urban Intelligence Backend (FastAPI + WebSockets)
"""

from collections import deque
import json
from pathlib import Path
import socket
import threading
import time
from typing import Any, Callable, Dict, List, Optional
import urllib.request
import numpy as np

try:
    import av
except ImportError:
    av = None

try:
    import cv2
except ImportError:
    cv2 = None

from ai.detectors.road_defect_detector import RoadDefectDetector
from ai.edge_optimizer import EdgeOptimizer


class SmartBusHardwareReceiver:
    def __init__(
        self,
        video_host: str = "0.0.0.0",
        video_port: int = 5000,
        metadata_host: str = "0.0.0.0",
        metadata_port: int = 5001,
        pi_ip: str = "100.111.145.77",
        result_port: int = 5002,
        yolo_model: str = "yolo26n.pt",
        output_file: str = "observations.jsonl",
        backend_url: Optional[str] = "http://localhost:8000",
        inference_interval: float = 0.05,
        max_gps_gap: float = 2.0,
        show_window: bool = True,
        window_name: str = "Smart Bus — SIH 26124 Edge Perception"
    ):
        self.video_host = video_host
        self.video_port = video_port
        self.metadata_host = metadata_host
        self.metadata_port = metadata_port
        self.pi_ip = pi_ip
        self.result_port = result_port
        self.yolo_model_path = yolo_model
        self.output_file = output_file
        self.backend_url = backend_url
        self.inference_interval = inference_interval
        self.max_gps_gap = max_gps_gap
        self.show_window = show_window
        self.window_name = window_name

        # State management
        self.state_lock = threading.Lock()
        self.running = False

        # Bus sync and telemetry
        self.bus_id: Optional[str] = None
        self.video_start_unix: Optional[float] = None
        self.gps_history: deque = deque(maxlen=30)

        # Video frames
        self.latest_frame: Optional[np.ndarray] = None
        self.latest_frame_pts: Optional[float] = None
        self.latest_frame_number: int = 0

        # Result socket back to Pi
        self.result_socket: Optional[socket.socket] = None
        self.result_socket_lock = threading.Lock()

        # Detector and optimizer
        self.detector: Optional[RoadDefectDetector] = None
        self.optimizer = EdgeOptimizer(evidence_dir="backend/static/evidence")

        # Optional callbacks for in-process integration
        self.on_event_callback: Optional[Callable[[Dict], None]] = None
        self.on_telemetry_callback: Optional[Callable[[Dict], None]] = None

    def _load_model(self):
        """Loads YOLO 26n trained defect weights."""
        print(f"[*] Loading YOLO Perception Model ({self.yolo_model_path})...")
        try:
            from ultralytics import YOLO
            # Check candidate weights
            weights_candidates = [
                self.yolo_model_path,
                "models/road_defect_yolo26n.pt",
                "yolo26n.pt",
                "models/yolo26n.pt",
                "yolov8n.pt"
            ]
            loaded_model = None
            for cand in weights_candidates:
                p = Path(cand)
                if p.exists() and p.is_file() and p.stat().st_size > 1024:
                    print(f"[*] Loaded trained weights from: {cand}")
                    loaded_model = YOLO(cand)
                    break
            
            if loaded_model is None:
                print("[!] Using default YOLO nano pretrained model.")
                loaded_model = YOLO("yolov8n.pt")

            self.detector = RoadDefectDetector(yolo_model=loaded_model, conf_thresh=0.30)
        except Exception as e:
            print(f"[!] Warning: YOLO initialization fallback: {e}")
            self.detector = RoadDefectDetector(yolo_model=None, conf_thresh=0.30)

    # --------------------------------------------------------
    # METADATA SERVER (PORT 5001)
    # --------------------------------------------------------
    def _metadata_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.metadata_host, self.metadata_port))
        server.listen(5)
        print(f"[META] Listening on {self.metadata_host}:{self.metadata_port}")

        while self.running:
            try:
                server.settimeout(1.0)
                try:
                    client, address = server.accept()
                except socket.timeout:
                    continue

                print(f"[META] Connection from {address}")
                thread = threading.Thread(
                    target=self._handle_metadata_client,
                    args=(client,),
                    daemon=True
                )
                thread.start()
            except Exception as e:
                if self.running:
                    print(f"[META] Server error: {e}")
        try:
            server.close()
        except Exception:
            pass

    def _handle_metadata_client(self, client: socket.socket):
        buffer = b""
        try:
            while self.running:
                data = client.recv(4096)
                if not data:
                    break
                buffer += data

                while b"\n" in buffer:
                    raw_msg, buffer = buffer.split(b"\n", 1)
                    if not raw_msg:
                        continue
                    try:
                        msg = json.loads(raw_msg.decode("utf-8"))
                        self._handle_metadata_message(msg)
                    except json.JSONDecodeError:
                        print("[META] Invalid JSON received")
        except Exception as e:
            print(f"[META] Client error: {e}")
        finally:
            try:
                client.close()
            except Exception:
                pass
            print("[META] Client disconnected")

    def _handle_metadata_message(self, message: Dict):
        msg_type = message.get("type")

        if msg_type == "video_sync":
            new_bus_id = message.get("bus_id", "UNKNOWN")
            new_start = float(message["video_start_unix"])
            with self.state_lock:
                self.bus_id = new_bus_id
                self.video_start_unix = new_start

            print()
            print("[SYNC] Video timeline anchored at:")
            print(f"       Bus ID = {new_bus_id}")
            print(f"       Unix   = {new_start:.6f}")
            print()

        elif msg_type == "gps":
            gps = {
                "timestamp": float(message["timestamp"]),
                "latitude": float(message["latitude"]),
                "longitude": float(message["longitude"]),
                "speed_kmh": float(message.get("speed_kmh", 0.0))
            }
            with self.state_lock:
                self.gps_history.append(gps)

            # Ingest telemetry into backend platform
            self._post_telemetry_to_backend(gps)

    # --------------------------------------------------------
    # VIDEO RECEIVER (PORT 5000)
    # --------------------------------------------------------
    def _video_receiver(self):
        video_url = f"tcp://{self.video_host}:{self.video_port}?listen=1"
        print(f"[VIDEO] Listening on {self.video_host}:{self.video_port}")

        while self.running:
            if av is None:
                print("[VIDEO] PyAV not available. Waiting for stream...")
                time.sleep(2)
                continue

            try:
                container = av.open(
                    video_url,
                    mode="r",
                    options={
                        "fflags": "nobuffer+discardcorrupt",
                        "flags": "low_delay",
                        "avioflags": "direct",
                        "probesize": "2048",
                        "analyzeduration": "0"
                    }
                )
                print("[VIDEO] Pi connected to video stream")
                video_stream = container.streams.video[0]

                for frame in container.decode(video_stream):
                    if not self.running:
                        break
                    image = frame.to_ndarray(format="bgr24")
                    pts = frame.time

                    with self.state_lock:
                        self.latest_frame = image
                        self.latest_frame_pts = pts
                        self.latest_frame_number += 1

                try:
                    container.close()
                except Exception:
                    pass
            except Exception as e:
                if self.running:
                    print(f"[VIDEO] Connection/decode error: {e}")
                    time.sleep(1)

            if self.running:
                print("[VIDEO] Waiting for Pi video connection...")

    # --------------------------------------------------------
    # GPS INTERPOLATION
    # --------------------------------------------------------
    def get_gps_for_time(self, target_unix: float) -> Optional[Dict]:
        with self.state_lock:
            fixes = list(self.gps_history)

        if not fixes:
            return None

        if len(fixes) == 1:
            fix = fixes[0]
            if abs(target_unix - fix["timestamp"]) > self.max_gps_gap:
                return None
            return fix.copy()

        before = None
        after = None

        for fix in fixes:
            if fix["timestamp"] <= target_unix:
                before = fix
            if fix["timestamp"] >= target_unix:
                after = fix
                break

        if before is None:
            first = fixes[0]
            if abs(target_unix - first["timestamp"]) <= self.max_gps_gap:
                return first.copy()
            return None

        if after is None:
            last = fixes[-1]
            if abs(target_unix - last["timestamp"]) <= self.max_gps_gap:
                return last.copy()
            return None

        if before["timestamp"] == after["timestamp"]:
            return before.copy()

        # Linear interpolation between fixes
        t1 = before["timestamp"]
        t2 = after["timestamp"]
        ratio = (target_unix - t1) / (t2 - t1)

        latitude = before["latitude"] + ratio * (after["latitude"] - before["latitude"])
        longitude = before["longitude"] + ratio * (after["longitude"] - before["longitude"])
        speed = before["speed_kmh"] + ratio * (after["speed_kmh"] - before["speed_kmh"])

        return {
            "timestamp": target_unix,
            "latitude": latitude,
            "longitude": longitude,
            "speed_kmh": speed
        }

    # --------------------------------------------------------
    # CONNECT & SEND TO PI (PORT 5002)
    # --------------------------------------------------------
    def connect_to_pi(self) -> bool:
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                sock.settimeout(4)
                sock.connect((self.pi_ip, self.result_port))
                sock.settimeout(None)

                with self.result_socket_lock:
                    self.result_socket = sock

                print(f"[RESULT] Connected to Pi at {self.pi_ip}:{self.result_port}")
                return True
            except Exception as e:
                print(f"[RESULT] Could not connect to Pi ({self.pi_ip}:{self.result_port}): {e}")
                try:
                    sock.close()
                except Exception:
                    pass
                time.sleep(2)
        return False

    def send_observation_to_pi(self, observation: Dict):
        message = json.dumps(observation, separators=(",", ":")) + "\n"
        encoded = message.encode("utf-8")

        with self.result_socket_lock:
            current_sock = self.result_socket

        if current_sock is None:
            return

        try:
            current_sock.sendall(encoded)
        except Exception as e:
            print(f"[RESULT] Send to Pi failed: {e}")
            with self.result_socket_lock:
                try:
                    current_sock.close()
                except Exception:
                    pass
                if self.result_socket is current_sock:
                    self.result_socket = None

    # --------------------------------------------------------
    # SAVE OBSERVATION LOCALLY
    # --------------------------------------------------------
    def save_observation(self, observation: Dict):
        try:
            with open(self.output_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(observation, separators=(",", ":")) + "\n")
        except Exception as e:
            print(f"[OUTPUT] Failed to save observation: {e}")

    # --------------------------------------------------------
    # BACKEND PLATFORM INGESTION
    # --------------------------------------------------------
    def _post_telemetry_to_backend(self, gps: Dict):
        with self.state_lock:
            cur_bus = self.bus_id or "BUS-101"

        payload = {
            "bus_id": cur_bus,
            "latitude": gps["latitude"],
            "longitude": gps["longitude"],
            "speed_kmh": gps.get("speed_kmh", 0.0),
            "heading_deg": 0.0,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(gps["timestamp"]))
        }

        if self.on_telemetry_callback:
            self.on_telemetry_callback(payload)

        if self.backend_url:
            def _async_post():
                try:
                    data = json.dumps(payload).encode("utf-8")
                    req = urllib.request.Request(
                        f"{self.backend_url}/api/v1/ingest/telemetry",
                        data=data,
                        headers={"Content-Type": "application/json"}
                    )
                    with urllib.request.urlopen(req, timeout=1.5):
                        pass
                except Exception:
                    pass
            threading.Thread(target=_async_post, daemon=True).start()

    def _post_observation_to_backend(self, event_payload: Dict):
        if self.on_event_callback:
            self.on_event_callback({"type": "NEW_EVENT", "payload": event_payload})

        if self.backend_url:
            def _async_post():
                try:
                    data = json.dumps(event_payload).encode("utf-8")
                    req = urllib.request.Request(
                        f"{self.backend_url}/api/v1/ingest/observation",
                        data=data,
                        headers={"Content-Type": "application/json"}
                    )
                    with urllib.request.urlopen(req, timeout=2.0):
                        pass
                except Exception:
                    pass
            threading.Thread(target=_async_post, daemon=True).start()

    # --------------------------------------------------------
    # MAIN RECEIVER & PROCESSING LOOP
    # --------------------------------------------------------
    def start(self):
        self.running = True

        print()
        print("================================================================")
        print("  SIH 26124 — Smart Bus Hardware Receiver & Ingestion Node")
        print("================================================================")
        print(f" Video stream listening: {self.video_host}:{self.video_port}")
        print(f" Metadata listening:     {self.metadata_host}:{self.metadata_port}")
        print(f" Pi return target:       {self.pi_ip}:{self.result_port}")
        print(f" YOLO Model:             {self.yolo_model_path}")
        print(f" Output Observations:    {self.output_file}")
        if self.backend_url:
            print(f" Platform Ingest API:    {self.backend_url}")
        print("================================================================")
        print()

        # 1. Clear / initialize output file
        with open(self.output_file, "w", encoding="utf-8") as f:
            pass

        # 2. Load model
        self._load_model()

        # 3. Start metadata server thread
        meta_thread = threading.Thread(target=self._metadata_server, daemon=True)
        meta_thread.start()

        # 4. Start video receiver thread
        vid_thread = threading.Thread(target=self._video_receiver, daemon=True)
        vid_thread.start()

        # 5. Connect to Pi result socket in background
        pi_res_thread = threading.Thread(target=self.connect_to_pi, daemon=True)
        pi_res_thread.start()

        # 6. Processing loop
        last_inference_time = 0.0
        annotated_frame = None
        observation_count = 0

        while self.running:
            with self.state_lock:
                if self.latest_frame is None:
                    frame = None
                    pts = None
                    frame_number = 0
                else:
                    frame = self.latest_frame.copy()
                    pts = self.latest_frame_pts
                    frame_number = self.latest_frame_number

                sync_time = self.video_start_unix
                current_bus_id = self.bus_id

            if frame is None:
                time.sleep(0.01)
                continue

            # Check if video sync is established
            if pts is None or sync_time is None:
                if self.show_window and cv2 is not None:
                    disp = frame.copy()
                    cv2.putText(
                        disp,
                        "Waiting for Pi video_sync metadata (port 5001)...",
                        (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.65,
                        (0, 0, 255),
                        2
                    )
                    cv2.imshow(self.window_name, disp)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        self.running = False
                        break
                continue

            capture_time = sync_time + pts
            latency = max(0.0, time.time() - capture_time)
            gps = self.get_gps_for_time(capture_time)
            now = time.time()

            # Run YOLO inference
            if now - last_inference_time >= self.inference_interval:
                speed_val = gps["speed_kmh"] if gps else 0.0
                defects = self.detector.detect(frame, speed_kmh=speed_val) if self.detector else []

                # Format detections for Pi observation message
                pi_detections = []
                for d in defects:
                    pi_detections.append({
                        "class": d["class_name"],
                        "confidence": d["confidence"],
                        "bbox": d["bbox"],
                        "severity": d["severity"],
                        "risk_score": d.get("risk_score"),
                        "risk_level": d.get("risk_level"),
                        "breadth_cm": d.get("breadth_cm"),
                        "depth_cm": d.get("depth_cm"),
                        "risk_assessment": d.get("risk_assessment")
                    })

                obs_payload = {
                    "bus_id": current_bus_id,
                    "capture_time": capture_time,
                    "video_pts": pts,
                    "latitude": gps["latitude"] if gps else None,
                    "longitude": gps["longitude"] if gps else None,
                    "speed_kmh": gps["speed_kmh"] if gps else None,
                    "detections": pi_detections
                }

                # 1. Save local observation
                self.save_observation(obs_payload)

                # 2. Send to Raspberry Pi
                self.send_observation_to_pi(obs_payload)

                # 3. Package & forward each defect to Urban Intelligence Backend
                if gps and defects:
                    telemetry_ctx = {
                        "latitude": gps["latitude"],
                        "longitude": gps["longitude"],
                        "speed_kmh": gps["speed_kmh"],
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(capture_time))
                    }
                    for d in defects:
                        is_water = "water" in d["class_name"]
                        evt = self.optimizer.package_observation(
                            bus_id=current_bus_id or "BUS-101",
                            telemetry=telemetry_ctx,
                            class_name=d["class_name"],
                            confidence=d["confidence"],
                            severity=d["severity"],
                            frame=frame,
                            bbox=d["bbox"],
                            frame_id=frame_number,
                            event_type="waterlogging" if is_water else "road_defect",
                            risk_score=d.get("risk_score"),
                            risk_level=d.get("risk_level"),
                            breadth_cm=d.get("breadth_cm"),
                            depth_cm=d.get("depth_cm"),
                            dimensions=d.get("dimensions"),
                            risk_assessment=d.get("risk_assessment")
                        )
                        if evt:
                            self._post_observation_to_backend(evt)

                observation_count += 1
                last_inference_time = now

                # Render annotated frame for display
                disp_frame = frame.copy()
                for d in defects:
                    bx1, by1, bx2, by2 = d["bbox"]
                    r_score = d.get("risk_score", 50)
                    r_lvl = d.get("risk_level", "Moderate")
                    b_cm = d.get("breadth_cm", 30)
                    d_cm = d.get("depth_cm")

                    if r_score >= 85:
                        col = (0, 0, 255)       # Red
                    elif r_score >= 65:
                        col = (0, 140, 255)     # Orange
                    elif r_score >= 40:
                        col = (0, 215, 255)     # Amber
                    else:
                        col = (0, 220, 100)     # Green

                    cv2.rectangle(disp_frame, (bx1, by1), (bx2, by2), col, 2)
                    lbl = f"{d['class_name'].upper()} [RISK {int(r_score)} {r_lvl.upper()} | {b_cm}cm"
                    if d_cm and "pothole" in d["class_name"]:
                        lbl += f" x {d_cm}cm"
                    lbl += "]"

                    (tw, th), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                    cv2.rectangle(disp_frame, (bx1, max(0, by1 - 20)), (bx1 + tw + 6, max(20, by1)), col, -1)
                    cv2.putText(disp_frame, lbl, (bx1 + 3, max(15, by1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0) if sum(col) > 400 else (255, 255, 255), 1, cv2.LINE_AA)

                annotated_frame = disp_frame

                if observation_count % 10 == 0:
                    gps_str = f"{gps['latitude']:.6f}, {gps['longitude']:.6f}" if gps else "waiting..."
                    spd_str = f"{gps['speed_kmh']:.1f} km/h" if gps else "waiting..."
                    print(
                        f"[OBS] #{observation_count} | Bus={current_bus_id} | "
                        f"Frame={frame_number} | GPS={gps_str} | Speed={spd_str} | "
                        f"Latency={latency:.3f}s | Hazards={len(defects)}"
                    )

            # Display window
            if self.show_window and cv2 is not None:
                display_frame = (annotated_frame if annotated_frame is not None else frame).copy()
                
                # Draw top HUD
                cv2.rectangle(display_frame, (0, 0), (display_frame.shape[1], 40), (20, 20, 20), -1)
                hud1 = f"BUS: {current_bus_id} | FRAME: {frame_number} | OBS: {observation_count} | LATENCY: {latency:.3f}s"
                if gps:
                    hud2 = f"GPS: {gps['latitude']:.5f}N, {gps['longitude']:.5f}E | SPEED: {gps['speed_kmh']:.1f} km/h | PI STREAM ACTIVE"
                else:
                    hud2 = "GPS: Waiting for GPS fixes on port 5001..."

                cv2.putText(display_frame, hud1, (10, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 200), 1, cv2.LINE_AA)
                cv2.putText(display_frame, hud2, (10, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (220, 220, 220), 1, cv2.LINE_AA)

                cv2.imshow(self.window_name, display_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q") or key == 27:
                    print("[!] User pressed quit.")
                    self.running = False
                    break

        self.stop()

    def stop(self):
        self.running = False
        with self.result_socket_lock:
            if self.result_socket is not None:
                try:
                    self.result_socket.close()
                except Exception:
                    pass
                self.result_socket = None

        if self.show_window and cv2 is not None:
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass

        print()
        print("================================================================")
        print(" Hardware Receiver Shutdown Completed")
        print(f" Observations saved to: {self.output_file}")
        print("================================================================")
