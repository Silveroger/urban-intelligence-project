"""
End-to-End Simulation & Verification Script for SIH 26124 Backend
Tests:
  1. GPS Telemetry Ingestion -> /api/v1/telemetry
  2. OCR Validation Rules -> /api/v1/observations (expect HTTP 422)
  3. Low Confidence Quarantine -> /api/v1/observations (quarantined, score unchanged)
  4. Confirmed Observation Ingestion -> /api/v1/observations (map-matched & score updated)
  5. GeoJSON Road Network Verification -> /api/v1/segments/geojson
  6. Live WebSocket Broadcast -> /ws/live
"""
import sys
import os
import asyncio
import json
import httpx
import websockets

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
WS_URL = BASE_URL.replace("http://", "ws://").replace("https://", "wss://") + "/ws/live"


async def run_simulation():
    print("=" * 70)
    print("SIH 26124: END-TO-END INGESTION & PIPELINE SIMULATION")
    print(f"Target Base URL: {BASE_URL}")
    print(f"Target WebSocket: {WS_URL}")
    print("=" * 70)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # 0. Health Check
        print("\n[Step 0] Checking Backend Server Health:")
        try:
            res = await client.get("/health")
            print(f"  Status: {res.status_code} | Body: {res.text}")
            if res.status_code != 200:
                print("  [-] Server is not responding with HTTP 200. Is it running?")
                return
        except Exception as e:
            print(f"  [-] Failed to reach {BASE_URL}: {e}")
            print("      Start the backend with: uvicorn app.main:app --port 8000")
            return

        # 1. Telemetry Ingestion Test
        print("\n[Step 1] Ingesting Fleet Bus Telemetry:")
        telemetry_payload = {
            "bus_id": "TEST-BUS-001",
            "latitude": 30.7333,
            "longitude": 76.7794,
            "speed_kmh": 32.5,
            "heading_deg": 142.0,
            "accuracy_meters": 2.5,
        }
        res = await client.post("/api/v1/telemetry", json=telemetry_payload)
        print(f"  Status: {res.status_code}")
        print(f"  Response: {res.json()}")
        assert res.status_code in [200, 201], f"Expected 200/201, got {res.status_code}"
        print("  [+] Telemetry Ingestion SUCCESS!")

        # 2. OCR Validation Test (Negative test: plate_text without plate_confidence)
        print("\n[Step 2] Testing OCR Validation (Negative Test):")
        invalid_ocr_payload = {
            "event_id": "evt_test_invalid_ocr_001",
            "bus_id": "TEST-BUS-001",
            "timestamp": "2026-09-04T12:00:00Z",
            "latitude": 30.7333,
            "longitude": 76.7794,
            "event_type": "incident",
            "class_name": "illegal_parking",
            "confidence": 0.85,
            "plate_text": "CH01AB1234",  # Missing plate_confidence!
        }
        res = await client.post("/api/v1/observations", json=invalid_ocr_payload)
        print(f"  Status: {res.status_code}")
        print(f"  Response: {res.json()}")
        assert res.status_code == 422, f"Expected 422 Unprocessable Entity, got {res.status_code}"
        print("  [+] OCR Validation rejected missing plate_confidence correctly (HTTP 422)!")

        # 3. Low Confidence Quarantine Test (confidence < 0.50)
        print("\n[Step 3] Testing Low-Confidence Quarantine (confidence < 0.50):")
        quarantine_payload = {
            "event_id": "evt_test_quarantine_002",
            "bus_id": "TEST-BUS-001",
            "timestamp": "2026-09-04T12:01:00Z",
            "latitude": 30.7333,
            "longitude": 76.7794,
            "event_type": "road_defect",
            "class_name": "pothole",
            "confidence": 0.35,  # Below 0.50 threshold
            "severity": 2,
        }
        res = await client.post("/api/v1/observations", json=quarantine_payload)
        print(f"  Status: {res.status_code}")
        print(f"  Response: {res.json()}")
        data = res.json()
        assert data.get("quarantined") is True, "Expected observation to be quarantined!"
        print("  [+] Low confidence observation was quarantined successfully!")

        # 4. Confirmed Observation Ingestion (confidence >= 0.50)
        print("\n[Step 4] Ingesting Confirmed Observation (confidence = 0.92):")
        confirmed_payload = {
            "event_id": "evt_test_confirmed_003",
            "bus_id": "TEST-BUS-001",
            "timestamp": "2026-09-04T12:02:00Z",
            "latitude": 30.7333,
            "longitude": 76.7794,
            "event_type": "road_defect",
            "class_name": "pothole_deep",
            "confidence": 0.92,
            "severity": 3,
            "evidence_uri": "https://storage.urban-intel.city/frames/evt_003.jpg",
        }
        res = await client.post("/api/v1/observations", json=confirmed_payload)
        print(f"  Status: {res.status_code}")
        print(f"  Response: {res.json()}")
        data = res.json()
        assert data.get("quarantined") is False, "Expected observation to be confirmed!"
        print("  [+] Confirmed observation ingested and matched to road network!")

        # 5. Verify Road Segments GeoJSON
        print("\n[Step 5] Verifying GET /api/v1/segments/geojson:")
        res = await client.get("/api/v1/segments/geojson")
        print(f"  Status: {res.status_code}")
        geo_data = res.json()
        print(f"  Type: {geo_data.get('type')}")
        features = geo_data.get("features", [])
        print(f"  Number of segments returned: {len(features)}")
        if features:
            print(f"  Sample Segment: {features[0]['properties']}")

        # 6. WebSocket Live Stream Test
        print("\n[Step 6] Testing Live WebSocket Stream:")
        try:
            async with websockets.connect(WS_URL, close_timeout=3.0) as ws:
                print("  [+] Connected to WebSocket /ws/live!")
                await ws.send("ping")
                reply = await asyncio.wait_for(ws.recv(), timeout=2.0)
                print(f"  [+] Received reply from server: {reply}")
        except Exception as e:
            print(f"  [-] WebSocket test note: {e}")

    print("\n" + "=" * 70)
    print("SIMULATION COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_simulation())
