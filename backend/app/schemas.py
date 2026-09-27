from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- Auth ---
class LoginRequest(BaseModel):
    email: str
    password: str

class LoginBody(BaseModel):
    identifier: str
    password: str

class RegisterRequest(BaseModel):
    role: str
    full_name: str
    mobile: Optional[str] = None
    email: str
    password: str
    confirm_password: str
    city_or_area: Optional[str] = None
    address: Optional[str] = None
    employee_id: Optional[str] = None
    vehicle_number: Optional[str] = None
    vehicle_type: Optional[str] = None
    assigned_area: Optional[str] = None
    assigned_route: Optional[str] = None
    driving_license: Optional[str] = None
    license_number: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    municipality_name: Optional[str] = None
    profile_photo: Optional[str] = None

class PasswordReset(BaseModel):
    email: str
    new_password: str
    confirm_password: str

class UserOut(BaseModel):
    id: int
    role: str
    full_name: str
    mobile: Optional[str] = None
    email: str
    city_or_area: Optional[str] = None
    address: Optional[str] = None
    employee_id: Optional[str] = None
    vehicle_number: Optional[str] = None
    vehicle_type: Optional[str] = None
    assigned_area: Optional[str] = None
    assigned_route: Optional[str] = None
    driving_license: Optional[str] = None
    license_number: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    municipality_name: Optional[str] = None
    profile_photo: Optional[str] = None
    status: str
    approved_date: Optional[datetime] = None
    approved_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    last_active: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class UserStatusUpdate(BaseModel):
    user_id: int
    status: str

class DriverApprove(BaseModel):
    rejection_reason: Optional[str] = None

class DriverAssign(BaseModel):
    assigned_area: Optional[str] = None
    assigned_route: Optional[str] = None
    vehicle_number: Optional[str] = None
    vehicle_type: Optional[str] = None

class DriverActivityOut(BaseModel):
    id: int
    driver_id: int
    action: str
    description: Optional[str] = None
    actor: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str
    status: Optional[str] = None
    email: Optional[str] = None
    panel: Optional[str] = None

# --- Employee ---
class EmployeeCreate(BaseModel):
    employee_id: str
    name: str
    email: str
    phone: Optional[str] = None
    password: str
    role: str = "employee"

class EmployeeOut(BaseModel):
    id: int
    employee_id: str
    name: str
    email: str
    phone: Optional[str] = None
    role: str
    reward_points: int
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# --- Dustbin ---
class DustbinCreate(BaseModel):
    dustbin_id: str
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class DustbinUpdate(BaseModel):
    fill_level: Optional[float] = None
    status: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class DustbinOut(BaseModel):
    id: int
    dustbin_id: str
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    fill_level: float
    status: str
    qr_code: Optional[str] = None
    created_at: Optional[datetime] = None
    last_update: Optional[datetime] = None
    class Config:
        from_attributes = True

# --- Unload ---
class UnloadRequest(BaseModel):
    dustbin_id: str
    employee_id: str

# --- Reward ---
class RedeemRequest(BaseModel):
    employee_id: str
    points: int
    description: str = "Reward redemption"

# --- Dashboard ---
class DashboardSummary(BaseModel):
    total_dustbins: int
    filled_dustbins: int
    ready_to_unload: int
    empty_dustbins: int
    total_employees: int
    total_unloads_today: int
    open_complaints: int

# --- Leaderboard ---
class LeaderboardEntry(BaseModel):
    rank: int
    employee_id: str
    name: str
    total_unloads: int
    reward_points: int

# --- Complaint ---
class ComplaintCreate(BaseModel):
    dustbin_id: str
    reporter_name: str
    reporter_phone: Optional[str] = None
    description: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_address: Optional[str] = None
    feedback: Optional[str] = None
    images: Optional[List[str]] = None

class ComplaintOut(BaseModel):
    id: int
    dustbin_id: int
    dustbin_code: Optional[str] = None
    dustbin_location: Optional[str] = None
    reporter_name: str
    reporter_phone: Optional[str] = None
    description: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_address: Optional[str] = None
    feedback: Optional[str] = None
    images: Optional[List[str]] = None
    status: str
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# --- Driver Collection ---
class CollectionCreate(BaseModel):
    dustbin_id: str
    employee_id: Optional[str] = None      # driver's employee_id
    driver_id: Optional[int] = None        # alt: driver user id
    waste_type: Optional[str] = None

class CollectionOut(BaseModel):
    id: int
    collection_id: str
    driver_id: int
    driver_name: str
    driver_employee_id: Optional[str] = None
    dustbin_id: int
    dustbin_code: str
    location: Optional[str] = None
    waste_type: Optional[str] = None
    status: str
    points: int
    collected_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class DriverCollectionsSummary(BaseModel):
    today_collections: int
    completed: int
    pending: int
    assigned_bins: int
    total_points: int

# --- Driver Location ---
class DriverLocationPost(BaseModel):
    driver_id: int
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None
    is_active: bool = True

class DriverLocationOut(BaseModel):
    driver_id: int
    driver_name: Optional[str] = None
    driver_employee_id: Optional[str] = None
    vehicle_number: Optional[str] = None
    assigned_area: Optional[str] = None
    assigned_route: Optional[str] = None
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None
    is_active: bool
    status: Optional[str] = None
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# --- Collection Task (automatic full-bin assignment) ---
class CollectionTaskOut(BaseModel):
    id: int
    task_id: str
    dustbin_id: int
    dustbin_code: str
    fill_level: float
    location: Optional[str] = None
    zone: Optional[str] = None
    priority: str
    assignment_mode: str
    status: str
    driver_id: Optional[int] = None
    driver_name: Optional[str] = None
    driver_employee_id: Optional[str] = None
    assigned_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    arrived_at: Optional[datetime] = None
    collecting_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    distance_km: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class TaskTransition(BaseModel):
    # optional fields used on some transitions (e.g. completion via scan)
    dustbin_code: Optional[str] = None
    driver_id: Optional[int] = None
    waste_type: Optional[str] = None

class TaskCreateBody(BaseModel):
    dustbin_id: str
    fill_level: Optional[float] = None
    zone: Optional[str] = None
    priority: Optional[str] = "HIGH"
    assignment_mode: Optional[str] = "AUTOMATIC"

class TaskAssignBody(BaseModel):
    driver_id: Optional[int] = None

class DriverStatusOut(BaseModel):
    driver_id: int
    full_name: Optional[str] = None
    employee_id: Optional[str] = None
    account_status: Optional[str] = None
    online: bool
    task_status: Optional[str] = None
    current_task_id: Optional[str] = None
    current_dustbin: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class TaskNotificationOut(BaseModel):
    id: int
    task_id: str
    dustbin_code: str
    fill_level: float
    driver_id: Optional[int] = None
    driver_name: Optional[str] = None
    driver_employee_id: Optional[str] = None
    distance_km: Optional[float] = None
    status: str
    message: Optional[str] = None
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True
