"""
SIH 26124 — Synthetic Test Video & GPS Track Generator
Generates realistic bus dashboard camera video streams with GPS tracks
for testing road defects, infrastructure gaps, traffic, and incidents.
"""

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np


def generate_synthetic_bus_run(
    output_video_path: str = "ai/sample_bus_camera.mp4",
    output_gps_path: str = "ai/sample_gps_track.json",
    duration_seconds: int = 10,
    fps: int = 24
):
    try:
        import cv2
    except ImportError:
        print("[!] OpenCV is required to generate synthetic test videos.")
        return

    out_video_p = Path(output_video_path)
    out_video_p.parent.mkdir(parents=True, exist_ok=True)
    out_gps_p = Path(output_gps_path)
    out_gps_p.parent.mkdir(parents=True, exist_ok=True)

    width, height = 640, 480
    total_frames = duration_seconds * fps
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_video_p), fourcc, fps, (width, height))

    # Route starting in Chandigarh Sector 17
    start_lat, start_lng = 30.7333, 76.7794
    end_lat, end_lng = 30.7420, 76.7890
    start_time = datetime.now(timezone.utc)

    gps_points = []

    for i in range(total_frames):
        t = i / total_frames
        curr_lat = start_lat + t * (end_lat - start_lat)
        curr_lng = start_lng + t * (end_lng - start_lng)
        curr_time = start_time + timedelta(seconds=(i / fps))

        # Log GPS every second
        if i % fps == 0 or i == total_frames - 1:
            gps_points.append({
                "timestamp": curr_time.isoformat(),
                "latitude": round(curr_lat, 6),
                "longitude": round(curr_lng, 6),
                "heading_deg": 135.0,
                "speed_kmh": 34.2
            })

        # Draw simulated road dashboard camera frame
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # Sky (Top 40%)
        frame[:int(height * 0.40), :] = [210, 180, 140]  # Light blueish sky
        # Road (Bottom 60%)
        frame[int(height * 0.40):, :] = [65, 65, 65]    # Asphalt dark gray

        # Road perspective trapezoid / lane markings
        pts = np.array([[int(width * 0.45), int(height * 0.40)], [int(width * 0.55), int(height * 0.40)], [width - 30, height], [30, height]], np.int32)
        cv2.fillPoly(frame, [pts], (80, 80, 80))

        # Lane divider stripes
        divider_y1 = int(height * 0.45)
        divider_y2 = int(height * 0.95)
        cv2.line(frame, (int(width * 0.5), divider_y1), (int(width * 0.5), divider_y2), (0, 220, 220), 3)

        # Draw simulated Pothole between frame 30 and 70
        if 30 <= i <= 70:
            pot_y = int(height * 0.65 + (i - 30) * 1.5)
            cv2.ellipse(frame, (int(width * 0.42), pot_y), (40, 22), 0, 0, 360, (20, 20, 20), -1)
            cv2.ellipse(frame, (int(width * 0.42), pot_y), (40, 22), 0, 0, 360, (5, 5, 5), 2)

        # Draw simulated Waterlogging patch between frame 100 and 140
        if 100 <= i <= 140:
            water_y = int(height * 0.70 + (i - 100) * 1.2)
            cv2.ellipse(frame, (int(width * 0.60), water_y), (60, 25), 0, 0, 360, (140, 120, 60), -1)

        # Draw Traffic Vehicle moving ahead
        veh_x = int(width * 0.58 + math.sin(i * 0.08) * 40)
        veh_y = int(height * 0.55)
        cv2.rectangle(frame, (veh_x, veh_y), (veh_x + 90, veh_y + 60), (40, 40, 180), -1) # Red Car
        cv2.rectangle(frame, (veh_x + 20, veh_y + 40), (veh_x + 70, veh_y + 55), (240, 240, 240), -1) # License Plate
        cv2.putText(frame, "CH01AB1234", (veh_x + 22, veh_y + 52), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)

        # Draw HUD overlay with Bus ID, Timestamp & Coordinates
        cv2.putText(frame, f"FLEET BUS-101 | FPS: {fps} | FRAME: {i:04d}", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.putText(frame, f"GPS: {curr_lat:.6f} N, {curr_lng:.6f} E", (15, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        writer.write(frame)

    writer.release()

    # Save GPS Track JSON
    with open(out_gps_p, "w", encoding="utf-8") as f:
        json.dump(gps_points, f, indent=2)

    print(f"[OK] Generated synthetic test video at '{output_video_path}' ({total_frames} frames).")
    print(f"[OK] Generated matching GPS track at '{output_gps_path}' ({len(gps_points)} telemetry points).")


if __name__ == "__main__":
    generate_synthetic_bus_run()
