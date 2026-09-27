from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from ..database import get_db
from ..models import Dustbin
from ..websocket_manager import ws_manager
from .tasks import ensure_task_for_dustbin, FULL_THRESHOLD

router = APIRouter()

# -------------------------------------------------------------
# PYDANTIC SCHEMAS FOR IOT PAYLOADS
# -------------------------------------------------------------
class IoTTelemetryPayload(BaseModel):
    dustbin_id: str = Field(..., description="Unique hardware identifier of the bin, e.g. 'DB001'")
    fill_level: Optional[float] = Field(None, ge=0.0, le=100.0, description="Fill percentage (0 to 100)")
    status: Optional[str] = Field(None, description="Optional status override: 'EMPTY', 'HALF', 'FILLED', 'FULL'")
    fire_detected: Optional[bool] = Field(False, description="True if flame/fire/smoke sensor is triggered")
    temperature: Optional[float] = Field(None, description="Current ambient or bin temperature in Celsius")
    smoke_ppm: Optional[float] = Field(None, description="Gas / smoke level from MQ2 sensor in PPM")
    battery_level: Optional[float] = Field(None, ge=0.0, le=100.0, description="Battery percentage (0 to 100)")
    latitude: Optional[float] = Field(None, description="Current GPS latitude")
    longitude: Optional[float] = Field(None, description="Current GPS longitude")
    timestamp: Optional[str] = Field(None, description="ISO timestamp from device or will be server-assigned")

class IoTFireEmergencyPayload(BaseModel):
    dustbin_id: str = Field(..., description="Dustbin ID where fire is detected")
    latitude: float = Field(..., description="GPS Latitude of the fire event")
    longitude: float = Field(..., description="GPS Longitude of the fire event")
    temperature: Optional[float] = Field(None, description="Flame/internal temperature reading")
    smoke_ppm: Optional[float] = Field(None, description="Smoke/gas sensor value")
    details: Optional[str] = Field("Fire/Flame detected by IoT sensor", description="Alert description")
    timestamp: Optional[str] = Field(None, description="Device timestamp")


# -------------------------------------------------------------
# REST ENDPOINTS FOR IOT DEVICES (ESP32 / SENSORS / RASPBERRY PI)
# -------------------------------------------------------------

@router.post("/telemetry")
async def receive_iot_telemetry(payload: IoTTelemetryPayload, db: Session = Depends(get_db)):
    """
    Standard IoT sensor update endpoint.
    Handles ultrasonic fill level, GPS tracking, battery, and fire sensors.
    """
    dustbin = db.query(Dustbin).filter(Dustbin.dustbin_id == payload.dustbin_id).first()
    if not dustbin:
        # Auto-register if new hardware bin
        dustbin = Dustbin(
            dustbin_id=payload.dustbin_id,
            location=f"Sensor Node {payload.dustbin_id}",
            latitude=payload.latitude or 12.9716,
            longitude=payload.longitude or 77.5946,
            fill_level=payload.fill_level or 0.0,
            status="EMPTY"
        )
        db.add(dustbin)
        db.commit()
        db.refresh(dustbin)

    # 1. Update GPS Coordinates if sent by device
    if payload.latitude is not None:
        dustbin.latitude = payload.latitude
    if payload.longitude is not None:
        dustbin.longitude = payload.longitude

    ts = payload.timestamp or datetime.utcnow().isoformat() + "Z"
    alerts_triggered = []

    # 2. EMERGENCY: Check if Fire is Detected
    if payload.fire_detected:
        dustbin.status = "FIRE_ALERT"
        db.commit()

        fire_alert_event = {
            "type": "FIRE_ALERT",
            "severity": "CRITICAL",
            "title": "🚨 FIRE EMERGENCY DETECTED!",
            "dustbin_id": dustbin.dustbin_id,
            "location": dustbin.location or "Unknown Location",
            "latitude": dustbin.latitude,
            "longitude": dustbin.longitude,
            "temperature": payload.temperature,
            "smoke_ppm": payload.smoke_ppm,
            "timestamp": ts,
            "action_required": "Immediate fire extinguishing / municipal dispatch needed"
        }
        await ws_manager.broadcast(fire_alert_event)
        alerts_triggered.append(fire_alert_event)

    # 3. Check Fill Level & Full Threshold
    if payload.fill_level is not None:
        dustbin.fill_level = payload.fill_level
        if payload.fill_level >= FULL_THRESHOLD:
            dustbin.status = "FULL"
            ensure_task_for_dustbin(db, dustbin)

            bin_full_event = {
                "type": "BIN_FULL_ALERT",
                "severity": "WARNING",
                "title": "🗑️ DUSTBIN FULL ALERT",
                "dustbin_id": dustbin.dustbin_id,
                "location": dustbin.location or "Unknown Location",
                "fill_level": dustbin.fill_level,
                "status": "FULL",
                "latitude": dustbin.latitude,
                "longitude": dustbin.longitude,
                "timestamp": ts
            }
            await ws_manager.broadcast(bin_full_event)
            alerts_triggered.append(bin_full_event)
        elif payload.fill_level >= 80:
            dustbin.status = "FILLED"
        elif payload.fill_level < 15:
            dustbin.status = "EMPTY"

    if payload.status and not payload.fire_detected:
        dustbin.status = payload.status

    db.commit()
    db.refresh(dustbin)

    # 4. Broadcast general telemetry update to live dashboards
    telemetry_event = {
        "type": "TELEMETRY_UPDATE",
        "dustbin_id": dustbin.dustbin_id,
        "fill_level": dustbin.fill_level,
        "status": dustbin.status,
        "latitude": dustbin.latitude,
        "longitude": dustbin.longitude,
        "location": dustbin.location,
        "battery_level": payload.battery_level,
        "temperature": payload.temperature,
        "timestamp": ts
    }
    await ws_manager.broadcast(telemetry_event)

    return {
        "status": "success",
        "message": "Telemetry received and broadcasted",
        "dustbin_id": dustbin.dustbin_id,
        "current_status": dustbin.status,
        "current_fill": dustbin.fill_level,
        "alerts_triggered": len(alerts_triggered)
    }


@router.post("/fire-alert")
async def trigger_fire_emergency(payload: IoTFireEmergencyPayload, db: Session = Depends(get_db)):
    """
    Dedicated high-priority Fire Emergency endpoint.
    Used by IoT thermal/flame sensors to trigger immediate sirens and emergency map popups.
    """
    dustbin = db.query(Dustbin).filter(Dustbin.dustbin_id == payload.dustbin_id).first()
    loc = dustbin.location if dustbin else f"Zone {payload.dustbin_id}"
    if dustbin:
        dustbin.status = "FIRE_ALERT"
        dustbin.latitude = payload.latitude
        dustbin.longitude = payload.longitude
        db.commit()

    ts = payload.timestamp or datetime.utcnow().isoformat() + "Z"

    event = {
        "type": "FIRE_ALERT",
        "severity": "CRITICAL",
        "title": "🚨 FIRE EMERGENCY DETECTED!",
        "dustbin_id": payload.dustbin_id,
        "location": loc,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "temperature": payload.temperature,
        "smoke_ppm": payload.smoke_ppm,
        "details": payload.details,
        "timestamp": ts,
        "maps_url": f"https://www.google.com/maps/search/?api=1&query={payload.latitude},{payload.longitude}"
    }

    # Broadcast immediately to all connected browsers/dashboards
    await ws_manager.broadcast(event)

    return {
        "status": "emergency_broadcasted",
        "event": event
    }


# -------------------------------------------------------------
# WEBSOCKET ENDPOINT FOR DASHBOARDS AND IOT CLIENTS
# -------------------------------------------------------------
@router.websocket("/ws")
async def iot_websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    """
    Real-time WebSocket endpoint:
    - Clients connect to ws://localhost:8000/iot/ws (or wss://... on production)
    - Receives live 'FIRE_ALERT', 'BIN_FULL_ALERT', and 'TELEMETRY_UPDATE' events.
    - IoT devices can also send JSON messages directly through this socket!
    """
    await ws_manager.connect(websocket)
    try:
        # Send initial confirmation handshake
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "message": "Connected to SmartBin IoT Live Alert Stream",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        while True:
            # IoT devices or clients can push JSON messages directly over WS
            data = await websocket.receive_json()
            event_type = data.get("type") or data.get("event")

            if event_type == "FIRE_ALERT" or data.get("fire_detected"):
                lat = data.get("latitude", 12.9720)
                lng = data.get("longitude", 77.5950)
                bid = data.get("dustbin_id", "UNKNOWN_BIN")
                fire_event = {
                    "type": "FIRE_ALERT",
                    "severity": "CRITICAL",
                    "title": "🚨 FIRE EMERGENCY DETECTED!",
                    "dustbin_id": bid,
                    "location": data.get("location", f"Dustbin {bid}"),
                    "latitude": lat,
                    "longitude": lng,
                    "temperature": data.get("temperature"),
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
                await ws_manager.broadcast(fire_event)

            elif event_type == "BIN_FULL" or (data.get("fill_level") is not None and float(data.get("fill_level", 0)) >= 80):
                full_event = {
                    "type": "BIN_FULL_ALERT",
                    "severity": "WARNING",
                    "title": "🗑️ DUSTBIN FULL ALERT",
                    "dustbin_id": data.get("dustbin_id", "DB001"),
                    "fill_level": data.get("fill_level", 95.0),
                    "status": "FULL",
                    "location": data.get("location", "Smart Dustbin"),
                    "latitude": data.get("latitude", 12.9716),
                    "longitude": data.get("longitude", 77.5946),
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
                await ws_manager.broadcast(full_event)
            else:
                # Echo / broadcast generic telemetry
                await ws_manager.broadcast(data)

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        ws_manager.disconnect(websocket)
