from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from ..database import get_db
from ..models import Employee, UnloadLog
from ..schemas import LeaderboardEntry

router = APIRouter()

@router.get("/weekly", response_model=List[LeaderboardEntry])
def weekly_leaderboard(db: Session = Depends(get_db)):
    results = (
        db.query(
            Employee.employee_id,
            Employee.name,
            Employee.reward_points,
            func.count(UnloadLog.id).label("total_unloads"),
        )
        .outerjoin(UnloadLog, UnloadLog.employee_id == Employee.id)
        .group_by(Employee.id, Employee.employee_id, Employee.name, Employee.reward_points)
        .order_by(func.count(UnloadLog.id).desc())
        .limit(20)
        .all()
    )
    return [
        LeaderboardEntry(
            rank=i + 1,
            employee_id=r.employee_id,
            name=r.name,
            total_unloads=r.total_unloads,
            reward_points=r.reward_points,
        )
        for i, r in enumerate(results)
    ]
