from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date

from ..database import get_db
from ..models import Dustbin, Employee, UnloadLog, Complaint, DriverCollection
from ..schemas import DashboardSummary

router = APIRouter()

@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    total = db.query(func.count(Dustbin.id)).scalar() or 0
    filled = db.query(func.count(Dustbin.id)).filter(
        (Dustbin.status == "FILLED") | (Dustbin.fill_level >= 80)
    ).scalar() or 0
    ready = db.query(func.count(Dustbin.id)).filter(Dustbin.status == "READY").scalar() or 0
    empty = db.query(func.count(Dustbin.id)).filter(
        (Dustbin.status == "EMPTY") & (Dustbin.fill_level < 80)
    ).scalar() or 0
    employees = db.query(func.count(Employee.id)).scalar() or 0
    today_unloads = db.query(func.count(UnloadLog.id)).filter(
        func.date(UnloadLog.timestamp) == date.today()
    ).scalar() or 0
    today_unloads += db.query(func.count(DriverCollection.id)).filter(
        func.date(DriverCollection.collected_at) == date.today()
    ).scalar() or 0
    open_complaints = db.query(func.count(Complaint.id)).filter(
        Complaint.status == "OPEN"
    ).scalar() or 0
    return DashboardSummary(
        total_dustbins=total,
        filled_dustbins=filled,
        ready_to_unload=ready,
        empty_dustbins=empty,
        total_employees=employees,
        total_unloads_today=today_unloads,
        open_complaints=open_complaints,
    )
