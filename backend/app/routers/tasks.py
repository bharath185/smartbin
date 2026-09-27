"""Automatic full-dustbin collection task assignment + state machine.

Architecture:
  * A CollectionTask is created the moment a dustbin crosses the FULL
    threshold (>= FULL_THRESHOLD, default 90%).
  * The system then searches for the best AVAILABLE driver and assigns the
    task automatically. If none is available the task stays PENDING_ASSIGNMENT
    and is retried whenever a driver frees up (see process_pending_assignments).
  * A single dustbin may only ever have ONE active (non-COMPLETED) task.

Driver eligibility rules (only these drivers may receive an automatic task):
  - account status is 'active' or 'verified'  (NOT suspended / pending / rejected)
  - online: has a fresh live GPS fix or recently posted location
  - not already carrying another active collection task
  - best-of selection when several match:
      1. same assigned zone as the dustbin
      2. closest GPS distance to the full dustbin
      3. lowest current workload (fewest active/last tasks)
      4. earliest to become available (longest idle)
"""
import math
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import (
    User,
    Dustbin,
    DriverLocation,
    DriverCollection,
    DriverActivity,
    CollectionTask,
)
from ..schemas import (
    CollectionTaskOut,
    TaskTransition,
    TaskCreateBody,
    TaskAssignBody,
    DriverStatusOut,
)

router = APIRouter()

FULL_THRESHOLD = 90.0        # dustbin fill % that triggers a collection task
STALE_SECONDS = 90           # a driver is considered offline without a fresh fix
ACTIVE_TASK_STATUSES = {
    "PENDING_ASSIGNMENT",
    "ASSIGNED",
    "ACCEPTED",
    "ON_ROUTE",
    "ARRIVED",
    "COLLECTING",
}
COMPLETED_STATUSES = {"COMPLETED", "CANCELLED"}
TRANSITION_ORDER = {
    "ASSIGNED": "ACCEPTED",
    "ACCEPTED": "ON_ROUTE",
    "ON_ROUTE": "ARRIVED",
    "ARRIVED": "COLLECTING",
    "COLLECTING": "COMPLETED",
}
PRIORITY = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def next_task_id(db: Session) -> str:
    count = db.query(func.count(CollectionTask.id)).scalar() or 0
    return f"T-{count + 1:06d}"


def _haversine(lat1, lng1, lat2, lng2):
    if lat1 is None or lng1 is None or lat2 is None or lng2 is None:
        return None
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _valid_coord(v):
    return v is not None and math.isfinite(v) and abs(v) > 0.0001


def _zone_of_dustbin(dustbin: Dustbin) -> str:
    if not dustbin:
        return ""
    loc = (dustbin.location or "").lower()
    zones = ["zone a", "zone b", "zone c", "zone d"]
    for z in zones:
        if z in loc:
            return z.title()
    return ""


def _is_online(driver: User, loc: DriverLocation | None) -> bool:
    if not driver:
        return False
    if driver.status not in ("active", "verified"):
        return False
    if loc is not None:
        # an explicit offline signal is authoritative
        if not loc.is_active:
            return False
        if loc.updated_at:
            age = (datetime.utcnow() - loc.updated_at.replace(tzinfo=None)).total_seconds()
            if age > STALE_SECONDS * 2:
                return False
        return True
    # no location row at all: fall back to last_active
    if driver.last_active:
        age = (datetime.utcnow() - driver.last_active.replace(tzinfo=None)).total_seconds()
        return age <= STALE_SECONDS * 2
    return False


def _active_driver_tasks(db: Session, driver_id: int):
    return db.query(CollectionTask).filter(
        CollectionTask.driver_id == driver_id,
        CollectionTask.status.in_(ACTIVE_TASK_STATUSES),
    ).count()


def _active_task_for_bin(db: Session, dustbin_id: int):
    return (
        db.query(CollectionTask)
        .filter(
            CollectionTask.dustbin_id == dustbin_id,
            CollectionTask.status.in_(ACTIVE_TASK_STATUSES),
        )
        .first()
    )


def _find_best_driver(db: Session, dustbin: Dustbin) -> User | None:
    """Pick the most suitable available driver or None."""
    bin_lat = getattr(dustbin, "latitude", None)
    bin_lng = getattr(dustbin, "longitude", None)
    zone = _zone_of_dustbin(dustbin)

    # occupied driver set (carrying another active task)
    busy = {
        r[0]
        for r in db.query(CollectionTask.driver_id)
        .filter(
            CollectionTask.driver_id.isnot(None),
            CollectionTask.status.in_(ACTIVE_TASK_STATUSES),
        )
        .all()
    }

    locations = {l.driver_id: l for l in db.query(DriverLocation).all()}
    candidates = []
    for d in db.query(User).filter(User.role == "driver").all():
        if d.id in busy:
            continue
        if d.status not in ("active", "verified"):
            continue
        loc = locations.get(d.id)
        if not _is_online(d, loc):
            continue
        same_zone = bool(zone and (d.assigned_area or "").strip().lower() == zone.lower())
        dist = None
        if _valid_coord(loc.latitude) and _valid_coord(loc.longitude):
            dist = _haversine(loc.latitude, loc.longitude, bin_lat, bin_lng)
        elif bin_lat is None:
            dist = None
        # workload = number of tasks this driver finished in the last 24h
        workload = (
            db.query(func.count(CollectionTask.id))
            .filter(
                CollectionTask.driver_id == d.id,
                CollectionTask.completed_at >= datetime.utcnow() - timedelta(days=1),
            )
            .scalar()
            or 0
        )
        # availability recency: last online time (earlier finished = available sooner)
        recency = loc.updated_at if (loc and loc.updated_at) else d.last_active
        candidates.append((same_zone, dist, workload, recency, d))

    if not candidates:
        return None

    def sort_key(c):
        same_zone, dist, workload, recency, d = c
        return (
            0 if same_zone else 1,
            dist if dist is not None else math.inf,
            workload,
            recency or datetime(1970, 1, 1),
        )

    candidates.sort(key=sort_key)
    return candidates[0][4]


def _tasks_sync(db: Session):
    """Trigger re-assignment of PENDING_ASSIGNMENT tasks and warn on leftovers."""
    process_pending_assignments(db, commit=False)


# ---------------------------------------------------------------------------
# assignment + task creation logic
# ---------------------------------------------------------------------------
def ensure_task_for_dustbin(
    db: Session,
    dustbin: Dustbin,
    zone: str | None = None,
    priority: str = "HIGH",
    assignment_mode: str = "AUTOMATIC",
    commit: bool = True,
) -> CollectionTask:
    """Create a task for a full dustbin (deduped) and auto-assign."""
    existing = _active_task_for_bin(db, dustbin.id)
    if existing:
        # refresh fill level if it increased
        if dustbin.fill_level and dustbin.fill_level > existing.fill_level:
            existing.fill_level = dustbin.fill_level
            existing.priority = priority or existing.priority
        if commit:
            db.commit()
        return existing

    task = CollectionTask(
        task_id=next_task_id(db),
        dustbin_id=dustbin.id,
        dustbin_code=dustbin.dustbin_id,
        fill_level=dustbin.fill_level or 0.0,
        location=dustbin.location,
        zone=zone or _zone_of_dustbin(dustbin) or "",
        priority=priority,
        assignment_mode=assignment_mode,
        status="PENDING_ASSIGNMENT",
    )
    db.add(task)
    db.flush()
    auto_assign_task(db, task, commit=False)
    if commit:
        db.commit()
        db.refresh(task)
    return task


def auto_assign_task(db: Session, task: CollectionTask, commit: bool = True):
    """Assign task.driver_id to the best available driver (only when eligible)."""
    if task.status not in ("PENDING_ASSIGNMENT", "ASSIGNED"):
        return task
    if task.status == "ASSIGNED" and task.driver_id:
        return task
    dustbin = db.query(Dustbin).filter(Dustbin.id == task.dustbin_id).first()
    if not dustbin:
        return task
    driver = _find_best_driver(db, dustbin)
    if not driver:
        task.status = "PENDING_ASSIGNMENT"
        if commit:
            db.commit()
        return task
    task.driver_id = driver.id
    task.driver_name = driver.full_name
    task.driver_employee_id = driver.employee_id
    task.status = "ASSIGNED"
    task.assigned_at = datetime.utcnow()
    loc = (
        db.query(DriverLocation).filter(DriverLocation.driver_id == driver.id).first()
    )
    if loc and _valid_coord(loc.latitude) and _valid_coord(loc.longitude):
        d = _haversine(loc.latitude, loc.longitude, dustbin.latitude, dustbin.longitude)
        task.distance_km = round(d, 2) if d is not None else None
    _log(db, driver.id, "assigned",
         f"Auto-assigned collection task {task.task_id} for {task.dustbin_code} "
         f"({round(task.fill_level)}% full) — {task.zone or 'Area'}")
    if commit:
        db.commit()
        db.refresh(task)
    return task


def process_pending_assignments(db: Session, commit: bool = True) -> int:
    """Re-attempt PENDING_ASSIGNMENT tasks (e.g. when a driver frees up)."""
    n = 0
    pending = (
        db.query(CollectionTask)
        .filter(CollectionTask.status == "PENDING_ASSIGNMENT")
        .order_by(CollectionTask.created_at.asc())
        .all()
    )
    for t in pending:
        before = t.status
        auto_assign_task(db, t, commit=False)
        if t.status != before:
            n += 1
    if commit:
        db.commit()
    return n


def _log(db: Session, driver_id: int, action: str, description: str, actor: str = "system"):
    db.add(DriverActivity(driver_id=driver_id, action=action, description=description, actor=actor))


# ---------------------------------------------------------------------------
# routes
# ---------------------------------------------------------------------------
@router.get("/assignments", response_model=list[CollectionTaskOut])
def municipality_assignments(db: Session = Depends(get_db)):
    """Active + recently completed assignments for the Municipality panel."""
    return (
        db.query(CollectionTask)
        .order_by(CollectionTask.updated_at.desc())
        .limit(100)
        .all()
    )


@router.get("/active", response_model=list[CollectionTaskOut])
def active_tasks(db: Session = Depends(get_db)):
    return (
        db.query(CollectionTask)
        .filter(CollectionTask.status.in_(ACTIVE_TASK_STATUSES))
        .order_by(CollectionTask.created_at.asc())
        .all()
    )


@router.get("/pending", response_model=list[CollectionTaskOut])
def pending_tasks(db: Session = Depends(get_db)):
    return (
        db.query(CollectionTask)
        .filter(CollectionTask.status.in_({"PENDING_ASSIGNMENT", "ASSIGNED"}))
        .order_by(CollectionTask.created_at.asc())
        .all()
    )


@router.get("/driver/{driver_id}/active", response_model=CollectionTaskOut | None)
def driver_active_task(driver_id: int, db: Session = Depends(get_db)):
    task = (
        db.query(CollectionTask)
        .filter(
            CollectionTask.driver_id == driver_id,
            CollectionTask.status.in_(
                {"ASSIGNED", "ACCEPTED", "ON_ROUTE", "ARRIVED", "COLLECTING"}
            ),
        )
        .order_by(CollectionTask.assigned_at.desc())
        .first()
    )
    return task


@router.get("/driver/{driver_id}", response_model=list[CollectionTaskOut])
def driver_tasks(driver_id: int, db: Session = Depends(get_db)):
    return (
        db.query(CollectionTask)
        .filter(CollectionTask.driver_id == driver_id)
        .order_by(CollectionTask.created_at.desc())
        .all()
    )


@router.get("/status", response_model=list[DriverStatusOut])
def driver_statuses(db: Session = Depends(get_db)):
    """Derived driver availability/state shared by both panels."""
    locations = {l.driver_id: l for l in db.query(DriverLocation).all()}
    active_tasks_by_driver = {}
    for t in (
        db.query(CollectionTask)
        .filter(
            CollectionTask.driver_id.isnot(None),
            CollectionTask.status.in_(ACTIVE_TASK_STATUSES),
        )
        .all()
    ):
        active_tasks_by_driver[t.driver_id] = t
    rows = []
    for d in db.query(User).filter(User.role == "driver").all():
        loc = locations.get(d.id)
        online = _is_online(d, loc)
        t = active_tasks_by_driver.get(d.id)
        task_status = None
        current_dustbin = None
        if d.status not in ("active", "verified"):
            task_status = "SUSPENDED" if d.status == "suspended" else d.status.upper()
        elif not online:
            task_status = "OFFLINE"
        elif t and t.status == "ASSIGNED":
            task_status = "ASSIGNED"
            current_dustbin = t.dustbin_code
        elif t and t.status == "ACCEPTED":
            task_status = "AVAILABLE" if False else "ACCEPTED"
            current_dustbin = t.dustbin_code
        elif t and t.status == "ON_ROUTE":
            task_status = "ON_ROUTE"
            current_dustbin = t.dustbin_code
        elif t and t.status == "ARRIVED":
            task_status = "ARRIVED"
            current_dustbin = t.dustbin_code
        elif t and t.status == "COLLECTING":
            task_status = "COLLECTING"
            current_dustbin = t.dustbin_code
        else:
            task_status = "AVAILABLE"
        rows.append(
            DriverStatusOut(
                driver_id=d.id,
                full_name=d.full_name,
                employee_id=d.employee_id,
                account_status=d.status,
                online=online,
                task_status=task_status,
                current_task_id=t.task_id if t else None,
                current_dustbin=current_dustbin,
                latitude=loc.latitude if loc else None,
                longitude=loc.longitude if loc else None,
            )
        )
    return rows


@router.post("/process-pending", response_model=dict)
def run_pending(db: Session = Depends(get_db)):
    n = process_pending_assignments(db)
    return {"processed": n}


@router.post("/", response_model=CollectionTaskOut, status_code=http_status.HTTP_201_CREATED)
def create_task(payload: TaskCreateBody, db: Session = Depends(get_db)):
    dustbin = db.query(Dustbin).filter(Dustbin.dustbin_id == payload.dustbin_id).first()
    if not dustbin:
        raise HTTPException(status_code=404, detail="Dustbin not found")
    if dustbin.fill_level is None:
        dustbin.fill_level = payload.fill_level or dustbin.fill_level
    if dustbin.fill_level < FULL_THRESHOLD:
        raise HTTPException(
            status_code=400,
            detail=f"Dustbin {dustbin.dustbin_id} is {round(dustbin.fill_level)}% full — below the {FULL_THRESHOLD:.0f}% threshold.",
        )
    task = ensure_task_for_dustbin(
        db,
        dustbin,
        zone=payload.zone,
        priority=payload.priority,
        assignment_mode=payload.assignment_mode,
    )
    db.refresh(dustbin)
    return task


@router.post("/assign", response_model=CollectionTaskOut)
def reassign(payload: TaskAssignBody, db: Session = Depends(get_db)):
    """Force re-run assignment for the earliest pending task (or empty all pending)."""
    n = process_pending_assignments(db, commit=False)
    db.commit()
    if n == 0:
        # no pending tasks — try to create for any currently full bin without a task
        created = 0
        for d in (
            db.query(Dustbin)
            .filter(Dustbin.fill_level >= FULL_THRESHOLD)
            .order_by(Dustbin.fill_level.desc())
            .all()
        ):
            if not _active_task_for_bin(db, d.id):
                ensure_task_for_dustbin(db, d, commit=False)
                created += 1
        if created:
            db.commit()
        return {"task": None, "created": created, "assigned": n}  # type: ignore
    return {"task": None, "created": 0, "assigned": n}  # type: ignore


@router.post("/{task_id}/accept", response_model=CollectionTaskOut)
def accept_task(task_id: str, db: Session = Depends(get_db)):
    return _transition(db, task_id, "accept", "ASSIGNED", "ACCEPTED")


@router.post("/{task_id}/start-route", response_model=CollectionTaskOut)
def start_route(task_id: str, db: Session = Depends(get_db)):
    return _transition(db, task_id, "start-route", "ACCEPTED", "ON_ROUTE")


@router.post("/{task_id}/arrive", response_model=CollectionTaskOut)
def arrive(task_id: str, db: Session = Depends(get_db)):
    return _transition(db, task_id, "arrive", "ON_ROUTE", "ARRIVED")


@router.post("/{task_id}/collect", response_model=CollectionTaskOut)
def collect(task_id: str, payload: TaskTransition, db: Session = Depends(get_db)):
    t = _get_task(db, task_id)
    if t.status not in ("ARRIVED", "COLLECTING"):
        raise HTTPException(status_code=400, detail=f"Cannot collect from status {t.status}")
    t.status = "COLLECTING"
    t.collecting_at = datetime.utcnow()
    if t.driver_id and _log_driver(db, t):
        _log(db, t.driver_id, "collecting", f"Driver collecting {t.dustbin_code} ({task_id})")
    db.commit()
    db.refresh(t)
    return t


@router.post("/{task_id}/complete", response_model=CollectionTaskOut)
def complete_task(task_id: str, payload: TaskTransition, db: Session = Depends(get_db)):
    """Complete the task after a successful unload (dustbin -> EMPTY)."""
    t = _get_task(db, task_id)
    if t.status == "COMPLETED":
        return t
    if t.status not in ("COLLECTING", "ARRIVED", "ON_ROUTE"):
        raise HTTPException(status_code=400, detail=f"Cannot complete from status {t.status}")
    dustbin = db.query(Dustbin).filter(Dustbin.id == t.dustbin_id).first()
    if dustbin:
        dustbin.fill_level = 0.0
        dustbin.status = "EMPTY"
    # record completion in history (reuse DriverCollection)
    if t.driver_id:
        hist = DriverCollection(
            collection_id=_next_collection_id(db),
            driver_id=t.driver_id,
            driver_name=t.driver_name or "",
            driver_employee_id=t.driver_employee_id,
            dustbin_id=t.dustbin_id,
            dustbin_code=t.dustbin_code,
            location=t.location,
            waste_type=payload.waste_type,
            status="COMPLETED",
            points=10,
            collected_at=datetime.utcnow(),
        )
        db.add(hist)
        _log(db, t.driver_id, "collected",
             f"Collected dustbin {t.dustbin_code} ({task_id}). +10 pts")
    t.status = "COMPLETED"
    t.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(t)
    # after completing, try to auto-assign any pending full-bin tasks
    process_pending_assignments(db)
    return t


def _next_collection_id(db: Session) -> str:
    count = db.query(func.count(DriverCollection.id)).scalar() or 0
    return f"COL-{count + 1:06d}"


def _get_task(db: Session, task_id: str) -> CollectionTask:
    safe = task_id.strip()
    t = (
        db.query(CollectionTask)
        .filter((CollectionTask.task_id == safe) | (CollectionTask.id == safe))
        .first()
    )
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    return t


def _log_driver(db: Session, t: CollectionTask) -> bool:
    # placeholder to avoid duplicate code below; driver assigned -> log
    return True


def _transition(db: Session, task_id: str, action: str, from_status: str, to_status: str):
    t = _get_task(db, task_id)
    if t.status != from_status:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot {action} from status {t.status} (expected {from_status})",
        )
    t.status = to_status
    now = datetime.utcnow()
    mapping = {
        "ACCEPTED": "accepted_at",
        "ON_ROUTE": "started_at",
        "ARRIVED": "arrived_at",
        "COLLECTING": "collecting_at",
        "COMPLETED": "completed_at",
    }
    if to_status in mapping:
        setattr(t, mapping[to_status], now)
    if t.driver_id:
        _log(db, t.driver_id, action,
             f"Driver {action.replace('-', ' ')} on {t.dustbin_code} ({task_id})")
    db.commit()
    db.refresh(t)
    return t