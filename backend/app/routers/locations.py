from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ..database import get_db
from ..models import DriverLocation, User
from ..schemas import DriverLocationPost, DriverLocationOut

router = APIRouter()


@router.post("/location", response_model=dict)
def update_driver_location(payload: DriverLocationPost, db: Session = Depends(get_db)):
    driver = db.query(User).filter(User.id == payload.driver_id, User.role == "driver").first()
    if not driver:
        return {"message": "Driver not found"}

    loc = db.query(DriverLocation).filter(DriverLocation.driver_id == payload.driver_id).first()
    if loc:
        loc.latitude = payload.latitude
        loc.longitude = payload.longitude
        loc.accuracy = payload.accuracy
        loc.speed = payload.speed
        loc.heading = payload.heading
        loc.is_active = 1 if payload.is_active else 0
    else:
        loc = DriverLocation(
            driver_id=payload.driver_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy=payload.accuracy,
            speed=payload.speed,
            heading=payload.heading,
            is_active=1 if payload.is_active else 0,
        )
        db.add(loc)

    driver.last_active = datetime.utcnow()
    db.commit()
    return {"message": "Location updated", "driver_id": payload.driver_id}

@router.get("/live", response_model=List[DriverLocationOut])
def get_live_locations(db: Session = Depends(get_db)):
    rows = (
        db.query(DriverLocation, User)
        .join(User, User.id == DriverLocation.driver_id)
        .order_by(DriverLocation.updated_at.desc())
        .all()
    )
    return [
        DriverLocationOut(
            driver_id=loc.driver_id,
            driver_name=user.full_name,
            driver_employee_id=user.employee_id,
            vehicle_number=user.vehicle_number,
            assigned_area=user.assigned_area,
            assigned_route=user.assigned_route,
            latitude=loc.latitude,
            longitude=loc.longitude,
            accuracy=loc.accuracy,
            speed=loc.speed,
            heading=loc.heading,
            is_active=bool(loc.is_active),
            status=user.status,
            updated_at=loc.updated_at,
        )
        for loc, user in rows
    ]
