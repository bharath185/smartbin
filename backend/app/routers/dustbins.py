from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from ..database import get_db
from ..models import Dustbin
from ..schemas import DustbinCreate, DustbinUpdate, DustbinOut
from .tasks import ensure_task_for_dustbin, FULL_THRESHOLD

router = APIRouter()

@router.get("/", response_model=List[DustbinOut])
def list_dustbins(db: Session = Depends(get_db)):
    return db.query(Dustbin).order_by(Dustbin.last_update.desc()).all()

@router.post("/", response_model=DustbinOut, status_code=status.HTTP_201_CREATED)
def create_dustbin(payload: DustbinCreate, db: Session = Depends(get_db)):
    existing = db.query(Dustbin).filter(Dustbin.dustbin_id == payload.dustbin_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Dustbin ID already exists")
    qr = f"SMARTBIN:{payload.dustbin_id}:{uuid.uuid4().hex[:8]}"
    dustbin = Dustbin(dustbin_id=payload.dustbin_id, location=payload.location,
                      latitude=payload.latitude, longitude=payload.longitude, qr_code=qr)
    db.add(dustbin)
    db.commit()
    db.refresh(dustbin)
    return dustbin

@router.get("/{dustbin_id}", response_model=DustbinOut)
def get_dustbin(dustbin_id: str, db: Session = Depends(get_db)):
    d = db.query(Dustbin).filter(Dustbin.dustbin_id == dustbin_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Dustbin not found")
    return d

def _apply_fill(db: Session, d: Dustbin, fill_level: float, status_override=None):
    d.fill_level = fill_level
    # FULL/critical level -> create automatic collection task
    if fill_level >= FULL_THRESHOLD:
        d.status = "FULL"
        ensure_task_for_dustbin(db, d)
    elif fill_level >= 80:
        d.status = "FILLED"
    elif fill_level < 10:
        d.status = "EMPTY"
    if status_override is not None:
        d.status = status_override
    return d

@router.put("/{dustbin_id}", response_model=DustbinOut)
def update_dustbin(dustbin_id: str, payload: DustbinUpdate, db: Session = Depends(get_db)):
    d = db.query(Dustbin).filter(Dustbin.dustbin_id == dustbin_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Dustbin not found")
    if payload.fill_level is not None:
        _apply_fill(db, d, payload.fill_level, payload.status)
    elif payload.status is not None:
        d.status = payload.status
    if payload.location is not None:
        d.location = payload.location
    if payload.latitude is not None:
        d.latitude = payload.latitude
    if payload.longitude is not None:
        d.longitude = payload.longitude
    db.commit()
    db.refresh(d)
    return d

@router.delete("/{dustbin_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dustbin(dustbin_id: str, db: Session = Depends(get_db)):
    d = db.query(Dustbin).filter(Dustbin.dustbin_id == dustbin_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Dustbin not found")
    db.delete(d)
    db.commit()

# IoT webhook - dustbin sends telemetry
@router.post("/telemetry")
def receive_telemetry(data: dict, db: Session = Depends(get_db)):
    d = db.query(Dustbin).filter(Dustbin.dustbin_id == data.get("dustbin_id")).first()
    if not d:
        raise HTTPException(status_code=404, detail="Dustbin not found")
    fill = data.get("fill_level")
    if fill is not None:
        d.fill_level = fill
        if fill >= FULL_THRESHOLD:
            d.status = "FULL"
            ensure_task_for_dustbin(db, d)
        elif fill >= 80:
            d.status = "FILLED"
    if data.get("status"):
        d.status = data["status"]
    db.commit()
    return {"message": "Telemetry received"}
