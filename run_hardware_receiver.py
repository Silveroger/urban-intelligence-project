"""
SIH 26124 — Hardware Receiver Standalone Runner (Smart Bus Laptop Mode)
Connects directly to the Raspberry Pi hardware on-board the bus:
- TCP Port 5000: Video stream
- TCP Port 5001: GPS metadata & video sync
- TCP Port 5002: Observation return to Pi
- Ingests detections with risk scores into the local Urban Intelligence Dashboard
"""

import argparse
import json
import socket
import sys
import threading
import time
from pathlib import Path

from ai.hardware_receiver import SmartBusHardwareReceiver


def simulate_raspberry_pi(
    video_port: int = 5000,
    meta_port: int = 5001,
    result_port: int = 5002,
    bus_id: str = "PB-65-CTU-1042"
):
    """
    Simulates the Raspberry Pi hardware node by:
    1. Listening on result_port (5002) for laptop observation returns.
    2. Connecting to meta_port (5001) and sending video_sync & live GPS telemetry.
    3. Connecting to video_port (5000) and streaming sample dashcam frames via TCP.
    """
    print("\n[SIMULATOR] Starting Raspberry Pi Test Rig...")

    # 1. Start Result Listener on 5002
    def result_server():
        try:
            res_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            res_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            res_sock.bind(("127.0.0.1", result_port))
            res_sock.listen(1)
            print(f"[SIMULATOR] Pi Result Listener listening on 127.0.0.1:{result_port}")
            client, _ = res_sock.accept()
            print("[SIMULATOR] Laptop connected to Pi Result Listener!")
            buf = b""
            while True:
                data = client.recv(4096)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if line:
                        msg = json.loads(line.decode("utf-8"))
                        n_det = len(msg.get("detections", []))
                        # print(f"[SIMULATOR-RX] Pi received observation from laptop: {n_det} hazard(s) detected.")
        except Exception as e:
            # print(f"[SIMULATOR] Result server closed: {e}")
            pass

    threading.Thread(target=result_server, daemon=True).start()

    # Wait for laptop servers to start
    time.sleep(2.0)

    # 2. Connect to Metadata Server (5001)
    meta_sock = None
    for _ in range(10):
        try:
            meta_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            meta_sock.connect(("127.0.0.1", meta_port))
            print(f"[SIMULATOR] Connected to Laptop Metadata Server on port {meta_port}!")
            break
        except Exception:
            time.sleep(1.0)

    if meta_sock:
        # Send video_sync message
        video_start = time.time()
        sync_msg = {
            "type": "video_sync",
            "bus_id": bus_id,
            "video_start_unix": video_start
        }
        meta_sock.sendall(json.dumps(sync_msg).encode("utf-8") + b"\n")

        def gps_streamer():
            lat = 30.7333
            lng = 76.7794
            spd = 32.0
            step = 0
            while True:
                step += 1
                gps_msg = {
                    "type": "gps",
                    "timestamp": time.time(),
                    "latitude": lat + (step * 0.00015),
                    "longitude": lng + (step * 0.00012),
                    "speed_kmh": round(spd + (step % 5) * 1.5, 1)
                }
                try:
                    meta_sock.sendall(json.dumps(gps_msg).encode("utf-8") + b"\n")
                except Exception:
                    break
                time.sleep(1.0)

        threading.Thread(target=gps_streamer, daemon=True).start()

    # 3. Stream sample video to Video Port (5000) using OpenCV or PyAV
    def video_streamer():
        import cv2
        time.sleep(1.5)
        # Sample video or synthetic video
        sample_path = "ai/sample_bus_camera.mp4"
        if not Path(sample_path).exists():
            from ai.test_video_generator import generate_synthetic_bus_run
            generate_synthetic_bus_run()

        # Connect as TCP client to tcp://127.0.0.1:5000?listen=1
        for _ in range(10):
            try:
                # Use PyAV or standard socket to stream raw / container
                import av
                out_container = av.open(
                    f"tcp://127.0.0.1:{video_port}",
                    mode="w",
                    format="flv"
                )
                stream = out_container.add_stream("h264", rate=25)
                stream.width = 1280
                stream.height = 720
                stream.pix_fmt = "yuv420p"

                in_cap = cv2.VideoCapture(sample_path)
                print(f"[SIMULATOR] Streaming video to Laptop on port {video_port}...")

                while in_cap.isOpened():
                    ret, frame = in_cap.read()
                    if not ret:
                        in_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue

                    # Encode to av VideoFrame
                    av_frame = av.VideoFrame.from_ndarray(frame, format="bgr24")
                    for packet in stream.encode(av_frame):
                        out_container.mux(packet)
                    time.sleep(0.04)

                out_container.close()
                in_cap.release()
                break
            except Exception as e:
                time.sleep(1.5)

    threading.Thread(target=video_streamer, daemon=True).start()


def main():
    parser = argparse.ArgumentParser(description="SIH 26124 — Smart Bus Hardware Receiver")
    parser.add_argument("--video-port", type=int, default=5000, help="TCP port for incoming video stream (default: 5000)")
    parser.add_argument("--meta-port", type=int, default=5001, help="TCP port for metadata & GPS stream (default: 5001)")
    parser.add_argument("--pi-ip", type=str, default="100.111.145.77", help="Raspberry Pi Tailscale / LAN IP (default: 100.111.145.77)")
    parser.add_argument("--result-port", type=int, default=5002, help="Port on Pi to send detection results back (default: 5002)")
    parser.add_argument("--yolo", dest="weights", default="yolo26n.pt", help="YOLO model path (default: yolo26n.pt)")
    parser.add_argument("--output", default="observations.jsonl", help="Output file for observations (default: observations.jsonl)")
    parser.add_argument("--backend", default="http://localhost:8000", help="FastAPI backend URL (default: http://localhost:8000)")
    parser.add_argument("--no-backend", action="store_true", help="Disable posting to backend API")
    parser.add_argument("--no-window", action="store_true", help="Run in headless mode without GUI window")
    parser.add_argument("--simulate-pi", action="store_true", help="Run built-in Raspberry Pi simulator for test runs")

    args = parser.parse_args()

    # If simulator requested, adjust Pi IP to localhost and start simulator thread
    target_pi_ip = "127.0.0.1" if args.simulate_pi else args.pi_ip
    backend_url = None if args.no_backend else args.backend

    if args.simulate_pi:
        simulate_raspberry_pi(
            video_port=args.video_port,
            meta_port=args.meta_port,
            result_port=args.result_port
        )

    receiver = SmartBusHardwareReceiver(
        video_host="0.0.0.0",
        video_port=args.video_port,
        metadata_host="0.0.0.0",
        metadata_port=args.meta_port,
        pi_ip=target_pi_ip,
        result_port=args.result_port,
        yolo_model=args.weights,
        output_file=args.output,
        backend_url=backend_url,
        show_window=not args.no_window
    )

    try:
        receiver.start()
    except KeyboardInterrupt:
        receiver.stop()


if __name__ == "__main__":
    main()
