"""
SmartBin WebSocket Connection & Payload Tester
Run this script to test the real-time WebSocket stream:
    python test_ws_client.py [ws_url]
"""
import sys
import json
import time

try:
    import websocket
except ImportError:
    print("Installing websocket-client...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websocket-client"])
    import websocket

DEFAULT_WS_URL = "ws://localhost:8000/iot/ws"

def on_message(ws, message):
    print("\n🟢 [INCOMING MESSAGE RECEIVED FROM SERVER]:")
    try:
        data = json.loads(message)
        print(json.dumps(data, indent=2))
        if data.get("type") == "FIRE_ALERT":
            print("🚨 >>> POPUP ALERT TRIGGERED FOR LAT:", data.get("latitude"), "LNG:", data.get("longitude"))
    except Exception:
        print(message)

def on_error(ws, error):
    print(f"\n🔴 [ERROR]: {error}")

def on_close(ws, close_status_code, close_msg):
    print("\n⚪ [WEBSOCKET CLOSED]")

def on_open(ws):
    print("\n✅ [CONNECTED SUCCESSFULLY TO WEBSOCKET SERVER]")
    print("Sending connection verification ping...")
    
    # 1. Verification Ping
    ping_payload = {
        "type": "PING",
        "client": "IoT_Device_Tester",
        "timestamp": time.time()
    }
    ws.send(json.dumps(ping_payload))
    print("Sent:", ping_payload)

    # 2. Simulate sending a Fire Emergency after 2 seconds
    def trigger_test():
        time.sleep(2)
        fire_test = {
            "type": "FIRE_ALERT",
            "dustbin_id": "DB002",
            "location": "Cafeteria Main Hall",
            "latitude": 12.972000,
            "longitude": 77.595000,
            "temperature": 88.5
        }
        print("\n🔥 Sending Live Fire Emergency Test Payload via WebSocket...")
        ws.send(json.dumps(fire_test))

    import threading
    threading.Thread(target=trigger_test, daemon=True).start()

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_WS_URL
    print(f"Connecting to: {url}")
    ws = websocket.WebSocketApp(url,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever()
