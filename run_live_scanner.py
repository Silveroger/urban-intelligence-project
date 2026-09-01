"""
SIH 26124 — Live AI Video Perception Scanner (Window Popup)
Launches the real-time AI perception engine in a dedicated interactive window
on your laptop screen with bounding boxes, HUD telemetry, and live detections.
"""

import sys
from pathlib import Path
from ai.pipeline import EdgeAIPipeline
from ai.test_video_generator import generate_synthetic_bus_run


def main():
    print("=" * 65)
    print(" SIH 26124 — Edge AI Live Perception Scanner")
    print("=" * 65)

    video_path = sys.argv[1] if len(sys.argv) > 1 else "ai/sample_bus_camera.mp4"
    gps_path = sys.argv[2] if len(sys.argv) > 2 else "ai/sample_gps_track.json"

    # If default sample video doesn't exist, create it
    if not Path(video_path).exists():
        print("[*] Generating sample bus dashcam video and GPS track...")
        generate_synthetic_bus_run(video_path, gps_path)

    print(f"[*] Loading Edge AI Pipeline (OpenCV + YOLO)...")
    print(f"[*] Processing Video: '{video_path}'")
    print(f"[*] GPS Track: '{gps_path}'")
    print(f"[*] Opening Live Scanning Window on screen...")
    print(f"[*] Tip: Press 'q' or 'ESC' on the video window to stop anytime.\n")

    pipeline = EdgeAIPipeline(bus_id="BUS-101")
    # show_window=True opens a dedicated OpenCV window on your screen
    summary = pipeline.process_video(
        video_path=video_path,
        gps_path=gps_path,
        show_window=True,
        delay_ms=30  # Adjust playback speed (30ms ~ 33 FPS)
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
