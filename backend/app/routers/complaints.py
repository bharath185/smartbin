from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime
import json

from ..database import get_db
from ..models import Complaint, Dustbin
from ..schemas import ComplaintCreate, ComplaintOut

router = APIRouter()

def _images_to_list(raw):
    if not raw:
        return None
    try:
        return json.loads(raw) if isinstance(raw, str) else list(raw)
    except Exception:
        return None

def _list_to_json(images):
    if not images:
        return None
    return json.dumps(images)

@router.get("/", response_model=List[ComplaintOut])
def list_complaints(status_filter: str = None, db: Session = Depends(get_db)):
    query = db.query(Complaint).order_by(Complaint.created_at.desc())
    if status_filter:
        query = query.filter(Complaint.status == status_filter.upper())
    results = query.all()
    out = []
    for c in results:
        dustbin = db.query(Dustbin).filter(Dustbin.id == c.dustbin_id).first()
        out.append(ComplaintOut(
            id=c.id,
            dustbin_id=c.dustbin_id,
            dustbin_code=dustbin.dustbin_id if dustbin else None,
            dustbin_location=dustbin.location if dustbin else None,
            reporter_name=c.reporter_name,
            reporter_phone=c.reporter_phone,
description=c.description,
            latitude=c.latitude,
            longitude=c.longitude,
            location_address=c.location_address,
            feedback=c.feedback,
            images=_images_to_list(c.images),
            status=c.status,
            created_at=c.created_at,
            resolved_at=c.resolved_at,
        ))
    return out

@router.post("/", response_model=ComplaintOut, status_code=status.HTTP_201_CREATED)
def create_complaint(payload: ComplaintCreate, db: Session = Depends(get_db)):
    dustbin = db.query(Dustbin).filter(Dustbin.dustbin_id == payload.dustbin_id).first()
    if not dustbin:
        raise HTTPException(status_code=404, detail="Dustbin not found. Please check the QR code.")
    complaint = Complaint(
        dustbin_id=dustbin.id,
        reporter_name=payload.reporter_name,
        reporter_phone=payload.reporter_phone,
        description=payload.description,
        latitude=payload.latitude,
        longitude=payload.longitude,
        location_address=payload.location_address,
        feedback=payload.feedback,
        images=_list_to_json(payload.images),
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return ComplaintOut(
        id=complaint.id,
        dustbin_id=complaint.dustbin_id,
        dustbin_code=dustbin.dustbin_id,
        dustbin_location=dustbin.location,
        reporter_name=complaint.reporter_name,
        reporter_phone=complaint.reporter_phone,
        description=complaint.description,
        latitude=complaint.latitude,
        longitude=complaint.longitude,
        location_address=complaint.location_address,
        feedback=complaint.feedback,
        images=_images_to_list(complaint.images),
        status=complaint.status,
        created_at=complaint.created_at,
        resolved_at=complaint.resolved_at,
    )

@router.put("/{complaint_id}/resolve")
def resolve_complaint(complaint_id: int, db: Session = Depends(get_db)):
    c = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
    c.status = "RESOLVED"
    c.resolved_at = datetime.utcnow()
    db.commit()
    return {"message": "Complaint resolved", "id": complaint_id}

@router.delete("/{complaint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_complaint(complaint_id: int, db: Session = Depends(get_db)):
    c = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
    db.delete(c)
    db.commit()
