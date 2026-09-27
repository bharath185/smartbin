from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import bcrypt
import jwt
import os
from datetime import datetime, timedelta

from ..database import get_db
from ..models import Employee, User, DriverActivity
from ..schemas import (
    LoginBody,
    RegisterRequest,
    PasswordReset,
    UserStatusUpdate,
    UserOut,
    TokenResponse,
    DriverApprove,
    DriverAssign,
    DriverActivityOut,
)

router = APIRouter()
security = HTTPBearer()
SECRET_KEY = os.getenv("JWT_SECRET", "smartbin-secret-key-change-in-prod")

ROLES = {"customer", "driver", "municipality"}
INITIAL_STATUS = {"customer": "active", "driver": "pending", "municipality": "pending"}
ALLOWED_STATUS = {"active", "suspended", "pending", "verified", "rejected", "approved"}
DRIVER_ACTIVE_STATUSES = {"active", "verified"}  # verified kept as legacy-active
# employees (admin accounts) map to the municipality panel
EMPLOYEE_PANEL = {"municipality", "admin", "super-admin", "officer"}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def _validate_password(password: str):
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long.")
    if not any(c.isdigit() for c in password) or not any(c.isalpha() for c in password):
        raise HTTPException(status_code=400, detail="Password must contain at least one letter and one number.")


def _issue_token(subject: str, role: str, panel: str) -> str:
    payload = {
        "sub": subject,
        "role": role,
        "panel": panel,
        "exp": datetime.utcnow() + timedelta(hours=8),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    sub = payload.get("sub", "")
    user = db.query(User).filter(User.email == sub).first()
    if user:
        return user
    emp = db.query(Employee).filter(Employee.email == sub).first()
    if emp:
        return emp
    raise HTTPException(status_code=401, detail="Account not found")


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        role=user.role,
        full_name=user.full_name,
        mobile=user.mobile,
        email=user.email,
        city_or_area=user.city_or_area,
        address=user.address,
        employee_id=user.employee_id,
        vehicle_number=user.vehicle_number,
        vehicle_type=user.vehicle_type,
        assigned_area=user.assigned_area,
        assigned_route=user.assigned_route,
        driving_license=user.driving_license,
        license_number=user.license_number or user.driving_license,
        department=user.department,
        designation=user.designation,
        municipality_name=user.municipality_name,
        profile_photo=user.profile_photo,
        status=user.status,
        approved_date=user.approved_date,
        approved_by=user.approved_by,
        rejection_reason=user.rejection_reason,
        last_active=user.last_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _log_activity(db: Session, driver_id: int, action: str, description: str, actor: str = "municipality"):
    db.add(DriverActivity(driver_id=driver_id, action=action, description=description, actor=actor))


@router.post("/login", response_model=TokenResponse)
def login(req: LoginBody, db: Session = Depends(get_db)):
    ident = req.identifier.strip()
    user = db.query(User).filter((User.email == ident) | (User.mobile == ident)).first()
    if user:
        if not verify_password(req.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if user.role == "driver":
            if user.status == "pending":
                raise HTTPException(status_code=403, detail="Your account is pending municipality approval.")
            if user.status == "rejected":
                raise HTTPException(status_code=403, detail="Your driver registration request was rejected. Please contact the municipality.")
            if user.status == "suspended":
                raise HTTPException(status_code=403, detail="Your driver account has been suspended. Please contact the municipality.")
            if user.status in DRIVER_ACTIVE_STATUSES:
                user.last_active = datetime.utcnow()
                db.commit()
        if user.role == "municipality" and user.status in ("pending", "rejected"):
            raise HTTPException(status_code=403, detail="Your municipality account awaits admin approval.")
        if user.role == "customer" and user.status == "suspended":
            raise HTTPException(status_code=403, detail="Your account has been suspended.")
        token = _issue_token(user.email, user.role, user.role)
        return TokenResponse(
            access_token=token,
            role=user.role,
            name=user.full_name,
            status=user.status,
            email=user.email,
            panel=user.role,
        )
    emp = db.query(Employee).filter(Employee.email == ident).first()
    if emp and verify_password(req.password, emp.hashed_password):
        token = _issue_token(emp.email, "municipality", "municipality")
        return TokenResponse(
            access_token=token,
            role="municipality",
            name=emp.name,
            status="approved",
            email=emp.email,
            panel="municipality",
        )
    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/register", response_model=UserOut, status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    role = req.role.strip().lower()
    if role not in ROLES:
        raise HTTPException(status_code=400, detail="Role must be customer, driver or municipality.")
    if req.password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")
    _validate_password(req.password)
    email = req.email.strip().lower()
    exists_user = db.query(User).filter(User.email == email).first()
    exists_emp = db.query(Employee).filter(Employee.email == email).first()
    if exists_user or exists_emp:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    if req.mobile:
        dup = db.query(User).filter(User.mobile == req.mobile.strip()).first()
        if dup:
            raise HTTPException(status_code=409, detail="An account with this mobile number already exists.")

    user = User(
        role=role,
        full_name=req.full_name.strip(),
        mobile=req.mobile.strip() if req.mobile else None,
        email=email,
        hashed_password=hash_password(req.password),
        city_or_area=req.city_or_area.strip() if req.city_or_area else None,
        address=req.address.strip() if req.address else None,
        employee_id=req.employee_id.strip() if req.employee_id else None,
        vehicle_number=req.vehicle_number.strip() if req.vehicle_number else None,
        vehicle_type=req.vehicle_type.strip() if req.vehicle_type else None,
        assigned_area=req.assigned_area.strip() if req.assigned_area else None,
        assigned_route=req.assigned_route.strip() if req.assigned_route else None,
        driving_license=req.driving_license.strip() if req.driving_license else None,
        license_number=(req.license_number or req.driving_license).strip() if (req.license_number or req.driving_license) else None,
        department=req.department.strip() if req.department else None,
        designation=req.designation.strip() if req.designation else None,
        municipality_name=req.municipality_name.strip() if req.municipality_name else None,
        profile_photo=req.profile_photo.strip() if req.profile_photo else None,
        status=INITIAL_STATUS[role],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    if role == "driver":
        _log_activity(db, user.id, "registered", f"Driver account registered and awaiting approval")
        db.commit()
    return _user_out(user)


@router.post("/forgot-password")
def forgot_password(req: PasswordReset, db: Session = Depends(get_db)):
    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")
    _validate_password(req.new_password)
    user = db.query(User).filter(User.email == req.email.strip().lower()).first()
    if not user:
        emp = db.query(Employee).filter(Employee.email == req.email.strip().lower()).first()
        if not emp:
            raise HTTPException(status_code=404, detail="No account found with this email.")
        emp.hashed_password = hash_password(req.new_password)
        db.commit()
        return {"message": "Password reset successful. You can now log in."}
    user.hashed_password = hash_password(req.new_password)
    db.commit()
    return {"message": "Password reset successful. You can now log in."}


@router.get("/me", response_model=UserOut)
def me(user=Depends(get_current_user)):
    if isinstance(user, Employee):
        return UserOut(
            id=user.id,
            role="municipality",
            full_name=user.name,
            email=user.email,
            status="approved",
            created_at=user.created_at,
        )
    return _user_out(user)


@router.get("/accounts", response_model=list[UserOut])
def list_accounts(role: str | None = None, db: Session = Depends(get_db)):
    q = db.query(User)
    if role:
        role = role.strip().lower()
        if role not in ROLES:
            raise HTTPException(status_code=400, detail="Invalid role filter.")
        q = q.filter(User.role == role)
    users = q.order_by(User.created_at.desc()).limit(200).all()
    return [_user_out(u) for u in users]


@router.post("/admin/status", response_model=UserOut)
def update_status(req: UserStatusUpdate, db: Session = Depends(get_db)):
    if req.status not in ALLOWED_STATUS:
        raise HTTPException(status_code=400, detail="Invalid status value.")
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.status = req.status
    db.commit()
    db.refresh(user)
    return _user_out(user)


# ---------------------------------------------------------------------------
#  Driver management (municipality workflows)
# ---------------------------------------------------------------------------
def _get_driver(user_id: int, db: Session) -> User:
    user = db.query(User).filter(User.id == user_id, User.role == "driver").first()
    if not user:
        raise HTTPException(status_code=404, detail="Driver not found.")
    return user


@router.post("/drivers/{user_id}/approve", response_model=UserOut)
def approve_driver(user_id: int, db: Session = Depends(get_db)):
    user = _get_driver(user_id, db)
    user.status = "active"
    user.approved_date = datetime.utcnow()
    user.approved_by = "municipality"
    user.rejection_reason = None
    _log_activity(db, user.id, "approved", f"Driver account approved", actor="municipality")
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.post("/drivers/{user_id}/reject", response_model=UserOut)
def reject_driver(user_id: int, payload: DriverApprove, db: Session = Depends(get_db)):
    user = _get_driver(user_id, db)
    user.status = "rejected"
    user.rejection_reason = payload.rejection_reason.strip() if payload.rejection_reason else None
    user.approved_date = None
    _log_activity(db, user.id, "rejected", f"Driver registration rejected" +
                  (f": {user.rejection_reason}" if user.rejection_reason else ""), actor="municipality")
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.post("/drivers/{user_id}/suspend", response_model=UserOut)
def suspend_driver(user_id: int, db: Session = Depends(get_db)):
    user = _get_driver(user_id, db)
    user.status = "suspended"
    _log_activity(db, user.id, "suspended", "Driver account suspended", actor="municipality")
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.post("/drivers/{user_id}/activate", response_model=UserOut)
def activate_driver(user_id: int, db: Session = Depends(get_db)):
    user = _get_driver(user_id, db)
    user.status = "active"
    user.approved_date = user.approved_date or datetime.utcnow()
    user.approved_by = user.approved_by or "municipality"
    user.rejection_reason = None
    _log_activity(db, user.id, "activated", "Driver account reactivated", actor="municipality")
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.put("/drivers/{user_id}/assign", response_model=UserOut)
def assign_driver(user_id: int, payload: DriverAssign, db: Session = Depends(get_db)):
    user = _get_driver(user_id, db)
    if payload.assigned_area is not None:
        user.assigned_area = payload.assigned_area.strip() or None
    if payload.assigned_route is not None:
        user.assigned_route = payload.assigned_route.strip() or None
    if payload.vehicle_number is not None:
        user.vehicle_number = payload.vehicle_number.strip() or None
    if payload.vehicle_type is not None:
        user.vehicle_type = payload.vehicle_type.strip() or None
    _log_activity(db, user.id, "assigned",
                  f"Assignment updated (area: {user.assigned_area or '—'}, route: {user.assigned_route or '—'})",
                  actor="municipality")
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.get("/drivers/{user_id}/activity", response_model=list[DriverActivityOut])
def driver_activity(user_id: int, db: Session = Depends(get_db)):
    _get_driver(user_id, db)
    rows = db.query(DriverActivity).filter(DriverActivity.driver_id == user_id) \
        .order_by(DriverActivity.created_at.desc()).limit(50).all()
    return rows


@router.delete("/drivers/{user_id}", status_code=204)
def delete_driver(user_id: int, db: Session = Depends(get_db)):
    user = _get_driver(user_id, db)
    db.query(DriverActivity).filter(DriverActivity.driver_id == user_id).delete()
    db.delete(user)
    db.commit()