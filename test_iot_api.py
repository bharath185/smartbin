"""
SmartBin IoT Device Simulator & WebSocket Test Script
Use this script to simulate an IoT sensor device sending:
  1. Regular telemetry updates
  2. Bin Full (>80%) alerts
  3. Fire Emergency alerts with GPS Coordinates
"""
import requests
import json
import time

SERVER_URL = "http://localhost:8000"

def send_telemetry(dustbin_id="DB001", fill_level=45.0, fire_detected=False, lat=12.9716, lng=77.5946):
    url = f"{SERVER_URL}/iot/telemetry"
    payload = {
        "dustbin_id": dustbin_id,
        "fill_level": fill_level,
        "fire_detected": fire_detected,
        "battery_level": 94.0,
        "latitude": lat,
        "longitude": lng,
        "temperature": 28.5
    }
    print(f"\n[IoT Node] Sending Telemetry to {url}:")
    print(json.dumps(payload, indent=2))
    try:
        resp = requests.post(url, json=payload, timeout=5)
        print(f"Response [{resp.status_code}]:", resp.json())
    except Exception as e:
        print(f"Connection failed (is backend running?): {e}")

def send_fire_alert(dustbin_id="DB002", lat=12.9720, lng=77.5950, temp=88.5):
    url = f"{SERVER_URL}/iot/fire-alert"
    payload = {
        "dustbin_id": dustbin_id,
        "latitude": lat,
        "longitude": lng,
        "temperature": temp,
        "smoke_ppm": 450.0,
        "details": "Flame detected by optical sensor in Bin #DB002"
    }
    print(f"\n🚨 [IoT Node] TRIGGERING FIRE EMERGENCY to {url}:")
    print(json.dumps(payload, indent=2))
    try:
        resp = requests.post(url, json=payload, timeout=5)
        print(f"Response [{resp.status_code}]:", resp.json())
    except Exception as e:
        print(f"Connection failed (is backend running?): {e}")

def send_bin_full(dustbin_id="DB001", lat=12.9716, lng=77.5946):
    print(f"\n🗑️ [IoT Node] Triggering Bin Full (95%) Update:")
    send_telemetry(dustbin_id=dustbin_id, fill_level=95.0, fire_detected=False, lat=lat, lng=lng)

if __name__ == "__main__":
    import sys
    print("=" * 60)
    print(" SmartBin IoT Hardware Simulator")
    print("=" * 60)
    print("Options:")
    print("  1: Send Normal Telemetry (45% fill)")
    print("  2: Send Bin Full Alert (95% fill)")
    print("  3: Send Fire Emergency Alert (Lat: 12.9720, Lng: 77.5950)")
    print("=" * 60)

    choice = sys.argv[1] if len(sys.argv) > 1 else "3"

    if choice == "1":
        send_telemetry()
    elif choice == "2":
        send_bin_full()
    elif choice == "3":
        send_fire_alert()
    else:
        print("Invalid choice")
