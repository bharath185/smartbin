from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from typing import List, Optional

from ..database import get_db
from ..models import Dustbin, User, DriverCollection, DriverActivity
from ..schemas import CollectionCreate, CollectionOut, DriverCollectionsSummary

router = APIRouter()


def next_collection_id(db: Session) -> str:
    count = db.query(func.count(DriverCollection.id)).scalar() or 0
    return f"COL-{count + 1:06d}"


def _resolve_driver(db: Session, payload: CollectionCreate):
    driver = None
    if payload.driver_id:
        driver = db.query(User).filter(User.id == payload.driver_id, User.role == "driver").first()
    if not driver and payload.employee_id:
        driver = db.query(User).filter(
            (User.employee_id == payload.employee_id) & (User.role == "driver")
        ).first()
        # fall back to municipality-created users that carry an employee id
        if not driver:
            driver = db.query(User).filter(User.employee_id == payload.employee_id).first()
    return driver


@router.post("/", response_model=CollectionOut, status_code=status.HTTP_201_CREATED)
def record_collection(payload: CollectionCreate, db: Session = Depends(get_db)):
    driver = _resolve_driver(db, payload)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    dustbin = db.query(Dustbin).filter(Dustbin.dustbin_id == payload.dustbin_id).first()
    if not dustbin:
        raise HTTPException(status_code=404, detail="Dustbin not found")

    points = 10
    coll = DriverCollection(
        collection_id=next_collection_id(db),
        driver_id=driver.id,
        driver_name=driver.full_name,
        driver_employee_id=driver.employee_id,
        dustbin_id=dustbin.id,
        dustbin_code=dustbin.dustbin_id,
        location=dustbin.location,
        waste_type=payload.waste_type,
        status="COMPLETED",
        points=points,
    )
    db.add(coll)
    # reset the dustbin on collection
    dustbin.fill_level = 0.0
    dustbin.status = "EMPTY"
    # record activity for the driver timeline
    act = DriverActivity(
        driver_id=driver.id,
        action="collected",
        description=f"Collected dustbin {dustbin.dustbin_id} ({payload.waste_type or 'Waste'}). +{points} pts",
        actor=driver.full_name,
    )
    db.add(act)
    db.commit()
    db.refresh(coll)
    return coll


@router.get("/", response_model=List[CollectionOut])
def list_collections(municipality: Optional[str] = None, db: Session = Depends(get_db)):
    return db.query(DriverCollection).order_by(DriverCollection.collected_at.desc()).all()


@router.get("/driver/{driver_id}", response_model=List[CollectionOut])
def driver_collections(driver_id: int, db: Session = Depends(get_db)):
    return (
        db.query(DriverCollection)
        .filter(DriverCollection.driver_id == driver_id)
        .order_by(DriverCollection.collected_at.desc())
        .all()
    )


@router.get("/driver/{driver_id}/summary", response_model=DriverCollectionsSummary)
def driver_summary(driver_id: int, db: Session = Depends(get_db)):
    driver = db.query(User).filter(User.id == driver_id).first()
    today_collections = (
        db.query(func.count(DriverCollection.id))
        .filter(
            (DriverCollection.driver_id == driver_id)
            & (func.date(DriverCollection.collected_at) == date.today())
        )
        .scalar()
        or 0
    )
    completed = (
        db.query(func.count(DriverCollection.id))
        .filter(DriverCollection.driver_id == driver_id, DriverCollection.status == "COMPLETED")
        .scalar()
        or 0
    )
    pending = (
        db.query(func.count(Dustbin.id))
        .filter((Dustbin.status == "READY") | (Dustbin.fill_level >= 40))
        .scalar()
        or 0
    )
    total_points = (
        db.query(func.coalesce(func.sum(DriverCollection.points), 0))
        .filter(DriverCollection.driver_id == driver_id)
        .scalar()
        or 0
    )
    assigned_bins = 0
    if driver:
        area = (driver.assigned_area or "").strip()
        if area:
            assigned_bins = (
                db.query(func.count(Dustbin.id))
                .filter(Dustbin.location.ilike(f"%{area}%") | Dustbin.location.ilike(f"%{driver.assigned_route or ''}%"))
                .scalar()
                or 0
            )
    return DriverCollectionsSummary(
        today_collections=today_collections,
        completed=completed,
        pending=pending,
        assigned_bins=assigned_bins,
        total_points=total_points,
    )
