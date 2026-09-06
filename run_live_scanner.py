"""
SIH 26124 — Live AI Video Perception Scanner (Window Popup)
Launches the real-time AI perception engine in a dedicated interactive window
on your laptop screen with bounding boxes, HUD telemetry, and live detections.
"""

import argparse
import sys
from pathlib import Path
from ai.pipeline import EdgeAIPipeline
from ai.test_video_generator import generate_synthetic_bus_run


def main():
    parser = argparse.ArgumentParser(description="SIH 26124 — Edge AI Live Perception Scanner")
    parser.add_argument("video", nargs="?", default=None, help="Path to video file, camera index (0, 1), or RTSP stream URL")
    parser.add_argument("gps", nargs="?", default=None, help="Path to synchronized GPS track (.json or .csv)")
    parser.add_argument("--cam", dest="cam", default=None, help="Hardware SBC camera index (0, 1) or stream URL (rtsp://...)")
    parser.add_argument("--weights", dest="weights", default=None, help="Custom YOLO weights (.pt or .onnx) file path")
    parser.add_argument("--bus-id", dest="bus_id", default="BUS-101", help="Bus / sensing vehicle identifier")
    parser.add_argument("--no-window", dest="no_window", action="store_true", help="Run headless without popup window")
    parser.add_argument("--hardware", dest="hardware", action="store_true", help="Launch in Smart Bus Hardware Receiver mode (TCP 5000/5001/5002)")
    parser.add_argument("--pi-ip", dest="pi_ip", default="100.111.145.77", help="Raspberry Pi IP address (default: 100.111.145.77)")
    parser.add_argument("--video-port", dest="video_port", type=int, default=5000, help="Video stream port (default: 5000)")
    parser.add_argument("--meta-port", dest="meta_port", type=int, default=5001, help="Metadata port (default: 5001)")
    parser.add_argument("--simulate-pi", dest="simulate_pi", action="store_true", help="Run with simulated Pi test rig")
    args = parser.parse_args()

    if args.hardware:
        from ai.hardware_receiver import SmartBusHardwareReceiver
        from run_hardware_receiver import simulate_raspberry_pi
        
        target_pi_ip = "127.0.0.1" if args.simulate_pi else args.pi_ip
        if args.simulate_pi:
            simulate_raspberry_pi(
                video_port=args.video_port,
                meta_port=args.meta_port,
                bus_id=args.bus_id
            )

        receiver = SmartBusHardwareReceiver(
            video_host="0.0.0.0",
            video_port=args.video_port,
            metadata_host="0.0.0.0",
            metadata_port=args.meta_port,
            pi_ip=target_pi_ip,
            yolo_model=args.weights or "yolo26n.pt",
            show_window=not args.no_window
        )
        try:
            receiver.start()
        except KeyboardInterrupt:
            receiver.stop()
        return

    print("=" * 65)
    print(" SIH 26124 — Edge AI Live Perception Scanner (Hardware & Edge)")
    print("=" * 65)

    video_input = args.cam or args.video or "ai/sample_bus_camera.mp4"
    gps_path = args.gps or "ai/sample_gps_track.json"

    # If default sample video doesn't exist and not using hardware camera, create it
    if not (str(video_input).isdigit() or str(video_input).startswith("rtsp://") or str(video_input).startswith("http://")):
        if not Path(video_input).exists():
            print("[*] Generating sample bus dashcam video and GPS track...")
            generate_synthetic_bus_run(video_input, gps_path)

    print(f"[*] Loading Edge AI Pipeline (YOLO 26n / OpenCV Engine)...")
    print(f"[*] Video Source / Camera Feed: '{video_input}'")
    print(f"[*] GPS Track Source: '{gps_path}'")
    if args.weights:
        print(f"[*] Custom Weights: '{args.weights}'")
    print(f"[*] Opening Live Scanning Window on screen...")
    print(f"[*] Tip: Press 'q' or 'ESC' on the video window to stop anytime.\n")

    pipeline = EdgeAIPipeline(bus_id=args.bus_id, weights_path=args.weights)
    summary = pipeline.process_video(
        video_path=video_input,
        gps_path=gps_path if Path(str(gps_path)).exists() else None,
        show_window=not args.no_window,
        delay_ms=30
    )

    print("\n" + "=" * 65)
    print(f" Scan Complete!")
    print(f" - Frames Processed: {summary['total_frames_analyzed']}")
    print(f" - Events Detected: {summary['total_events_detected']}")
    print(f" - Incidents Flagged: {summary['total_incidents_flagged']}")
    print(f" - Evidence crops saved to: backend/static/evidence/")
    print("=" * 65)


if __name__ == "__main__":
    main()
