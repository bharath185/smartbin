from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import bcrypt
from typing import List

from ..database import get_db
from ..models import Employee, UnloadLog, Dustbin, RewardTransaction
from ..schemas import EmployeeCreate, EmployeeOut, UnloadRequest, RedeemRequest

router = APIRouter()

@router.get("/", response_model=List[EmployeeOut])
def list_employees(db: Session = Depends(get_db)):
    return db.query(Employee).order_by(Employee.created_at.desc()).all()

@router.post("/", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db)):
    existing = db.query(Employee).filter(
        (Employee.employee_id == payload.employee_id) | (Employee.email == payload.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee ID or email already exists")
    emp = Employee(
        employee_id=payload.employee_id,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        hashed_password=bcrypt.hashpw(payload.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
        role=payload.role,
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp

@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(employee_id: str, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp

@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(employee_id: str, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    db.delete(emp)
    db.commit()

# --- Unload a dustbin (QR scan action) ---
@router.post("/unload")
def unload_dustbin(payload: UnloadRequest, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.employee_id == payload.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    dustbin = db.query(Dustbin).filter(Dustbin.dustbin_id == payload.dustbin_id).first()
    if not dustbin:
        raise HTTPException(status_code=404, detail="Dustbin not found")
    points = 10
    log = UnloadLog(dustbin_id=dustbin.id, employee_id=emp.id, points_earned=points)
    db.add(log)
    emp.reward_points += points
    dustbin.fill_level = 0.0
    dustbin.status = "EMPTY"
    tx = RewardTransaction(employee_id=emp.id, points=points, transaction_type="earned", description=f"Unloaded dustbin {dustbin.dustbin_id}")
    db.add(tx)
    db.commit()
    return {"message": f"Dustbin {dustbin.dustbin_id} unloaded by {emp.name}. +{points} points!", "total_points": emp.reward_points}

# --- Redeem reward points ---
@router.post("/redeem")
def redeem_points(payload: RedeemRequest, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.employee_id == payload.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    if emp.reward_points < payload.points:
        raise HTTPException(status_code=400, detail="Insufficient points")
    emp.reward_points -= payload.points
    tx = RewardTransaction(employee_id=emp.id, points=-payload.points, transaction_type="redeemed", description=payload.description)
    db.add(tx)
    db.commit()
    return {"message": f"Redeemed {payload.points} points", "remaining_points": emp.reward_points}
