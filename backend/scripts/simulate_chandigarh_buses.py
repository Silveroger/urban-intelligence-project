"""
Live Bus Telemetry Simulator for SIH 26124 Urban Intelligence Platform
Moves demo buses gradually along realistic Chandigarh road corridors.

Usage:
    python scripts/simulate_chandigarh_buses.py --steps 10
    python scripts/simulate_chandigarh_buses.py --loop --interval 1.5

Data Flow:
    Simulator -> POST /api/v1/telemetry -> FastAPI -> WebSocket /ws/live -> React Frontend
"""
import sys
import os
import time
import math
import argparse
import httpx
from datetime import datetime, timezone

# Corridor waypoints for active demo simulation loaded dynamically from canonical road geometries
CANONICAL_GEOJSON_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "chandigarh_roads_canonical.geojson")
)

def _load_canonical_routes():
    import json
    if not os.path.exists(CANONICAL_GEOJSON_PATH):
        raise FileNotFoundError(f"Canonical GeoJSON missing at {CANONICAL_GEOJSON_PATH}")
    with open(CANONICAL_GEOJSON_PATH, "r", encoding="utf-8") as f:
        geo = json.load(f)
    features = {feat["properties"]["segment_id"]: feat for feat in geo.get("features", [])}

    routes = {}
    bus_configs = [
        ("DEMO-BUS-001", "seg_chandigarh_001", "Madhya Marg Eastbound", 36.0),
        ("DEMO-BUS-002", "seg_chandigarh_002", "Dakshin Marg South-Eastbound", 42.0),
        ("DEMO-BUS-003", "seg_chandigarh_003", "Jan Marg Southbound", 28.0),
        ("DEMO-BUS-004", "seg_chandigarh_004", "Himalaya Marg Southbound", 32.0),
        ("DEMO-BUS-005", "seg_chandigarh_005", "Udyog Path Corridor", 25.0),
        ("DEMO-BUS-006", "seg_chandigarh_006", "Purv Marg Northbound", 38.0),
        ("DEMO-BUS-007", "seg_chandigarh_007", "Sarovar Path Southbound", 30.0),
        ("DEMO-BUS-008", "seg_chandigarh_008", "Vigyan Path Corridor", 35.0),
        ("DEMO-BUS-009", "seg_chandigarh_009", "Sukhna Path Eastbound", 40.0),
        ("DEMO-BUS-010", "seg_chandigarh_010", "Uttar Marg Lake Promenade", 33.0),
    ]
    for bus_id, seg_id, rname, speed in bus_configs:
        feat = features.get(seg_id)
        if feat:
            # Note: Coordinates in GeoJSON are [lng, lat], routes expect [(lat, lng), ...]
            pts = [(round(p[1], 6), round(p[0], 6)) for p in feat["geometry"]["coordinates"]]
            routes[bus_id] = {
                "name": rname,
                "speed": speed,
                "waypoints": pts,
            }
    return routes

ROUTES = _load_canonical_routes()


def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculates compass heading from point 1 to point 2 in degrees (0-360)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)
    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    bearing = math.degrees(math.atan2(y, x))
    return round((bearing + 360) % 360, 1)


def run_simulation(base_url: str, steps: int, loop: bool, interval: float):
    print("=" * 70)
    print("SIH 26124: CHANDIGARH FLEET BUS LIVE SIMULATOR")
    print(f"Target API: {base_url}/api/v1/telemetry")
    print(f"Buses Simulating: {len(ROUTES)}")
    print(f"Mode: {'Continuous Loop (Ctrl+C to stop)' if loop else f'Finite ({steps} steps)'}")
    print(f"Step Interval: {interval}s")
    print("=" * 70)

    client = httpx.Client(base_url=base_url, timeout=5.0)

    step = 0
    indices = {bus_id: 0 for bus_id in ROUTES}

    try:
        while True:
            step += 1
            print(f"\n--- Simulation Step {step} [{datetime.now().strftime('%H:%M:%S')}] ---")

            for bus_id, r_info in ROUTES.items():
                pts = r_info["waypoints"]
                idx = indices[bus_id]
                lat, lng = pts[idx]

                # Next waypoint for bearing
                next_idx = (idx + 1) % len(pts)
                next_lat, next_lng = pts[next_idx]
                heading = calculate_bearing(lat, lng, next_lat, next_lng)

                payload = {
                    "bus_id": bus_id,
                    "latitude": lat,
                    "longitude": lng,
                    "speed_kmh": r_info["speed"] + round((step % 5 - 2) * 1.5, 1),
                    "heading_deg": heading,
                    "accuracy_meters": 2.0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                try:
                    res = client.post("/api/v1/telemetry", json=payload)
                    if res.status_code in (200, 201):
                        data = res.json()
                        print(f"  [>] {bus_id} ({r_info['name']}): ({lat:.4f}, {lng:.4f}) | {heading}° | HTTP {res.status_code}")
                    else:
                        print(f"  [!] {bus_id} error: HTTP {res.status_code} - {res.text}")
                except Exception as e:
                    print(f"  [-] Connection error posting {bus_id}: {e}")

                indices[bus_id] = next_idx

            if not loop and step >= steps:
                print("\n[+] Target step count reached.")
                break

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n[!] Simulation stopped by user (Ctrl+C).")
    finally:
        client.close()
        print("\nSimulator finished.")


def main():
    parser = argparse.ArgumentParser(description="Chandigarh Bus Telemetry Simulator")
    parser.add_argument("--base-url", default="http://localhost:8000", help="FastAPI backend base URL")
    parser.add_argument("--steps", type=int, default=10, help="Number of steps to simulate (default: 10)")
    parser.add_argument("--loop", action="store_true", help="Run in continuous loop until Ctrl+C")
    parser.add_argument("--interval", type=float, default=1.5, help="Interval between steps in seconds (default: 1.5)")
    args = parser.parse_args()

    run_simulation(args.base_url, args.steps, args.loop, args.interval)


if __name__ == "__main__":
    main()
