from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import relationship
from .database import Base

class Dustbin(Base):
    __tablename__ = "dustbins"
    id = Column(Integer, primary_key=True, index=True)
    dustbin_id = Column(String(50), unique=True, index=True, nullable=False)
    location = Column(String(200), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    fill_level = Column(Float, default=0.0)
    status = Column(String(20), default="EMPTY")
    qr_code = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_update = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    unloads = relationship("UnloadLog", back_populates="dustbin")
    complaints = relationship("Complaint", back_populates="dustbin")

class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    hashed_password = Column(String(200), nullable=False)
    role = Column(String(20), default="employee")
    reward_points = Column(Integer, default=0)
    avatar_url = Column(String(300), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    unloads = relationship("UnloadLog", back_populates="employee")
    rewards = relationship("RewardTransaction", back_populates="employee")

class UnloadLog(Base):
    __tablename__ = "unload_logs"
    id = Column(Integer, primary_key=True, index=True)
    dustbin_id = Column(Integer, ForeignKey("dustbins.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    points_earned = Column(Integer, default=10)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    dustbin = relationship("Dustbin", back_populates="unloads")
    employee = relationship("Employee", back_populates="unloads")

class RewardTransaction(Base):
    __tablename__ = "reward_transactions"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    points = Column(Integer, nullable=False)
    transaction_type = Column(String(20), default="earned")
    description = Column(String(300), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    employee = relationship("Employee", back_populates="rewards")

class Complaint(Base):
    __tablename__ = "complaints"
    id = Column(Integer, primary_key=True, index=True)
    dustbin_id = Column(Integer, ForeignKey("dustbins.id"), nullable=False)
    reporter_name = Column(String(100), nullable=False)
    reporter_phone = Column(String(20), nullable=True)
    description = Column(Text, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_address = Column(String(300), nullable=True)
    feedback = Column(Text, nullable=True)
    images = Column(Text, nullable=True)   # JSON array of base64 data URLs
    status = Column(String(20), default="OPEN")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    dustbin = relationship("Dustbin", back_populates="complaints")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(20), default="customer")       # customer | driver | municipality
    full_name = Column(String(100), nullable=False)
    mobile = Column(String(20), nullable=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    city_or_area = Column(String(200), nullable=True)
    address = Column(String(300), nullable=True)            # driver residential address
    employee_id = Column(String(50), nullable=True)         # driver / municipality
    vehicle_number = Column(String(50), nullable=True)      # driver
    vehicle_type = Column(String(50), nullable=True)        # driver
    assigned_area = Column(String(200), nullable=True)      # driver
    assigned_route = Column(String(100), nullable=True)     # driver
    driving_license = Column(String(100), nullable=True)    # driver
    license_number = Column(String(100), nullable=True)     # driver (alias, kept consistent)
    department = Column(String(100), nullable=True)         # municipality
    designation = Column(String(100), nullable=True)        # municipality
    municipality_name = Column(String(200), nullable=True)  # municipality
    profile_photo = Column(String(300), nullable=True)
    status = Column(String(20), default="active")
    # customer: active | suspended
    # driver:   pending | active | suspended | rejected
    # municipality: pending | approved | rejected
    approved_date = Column(DateTime(timezone=True), nullable=True)   # driver/municipality
    approved_by = Column(String(100), nullable=True)                # who approved
    rejection_reason = Column(String(300), nullable=True)           # driver rejection reason
    last_active = Column(DateTime(timezone=True), nullable=True)    # driver last login
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    driver_activity = relationship("DriverActivity", back_populates="driver")


class DriverActivity(Base):
    __tablename__ = "driver_activity"
    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False)          # approved / rejected / suspended / activated / assigned / logged_in / updated
    description = Column(String(300), nullable=True)
    actor = Column(String(100), nullable=True)           # municipality admin email / driver
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    driver = relationship("User", back_populates="driver_activity")


class DriverLocation(Base):
    __tablename__ = "driver_locations"
    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=True)
    speed = Column(Float, nullable=True)
    heading = Column(Float, nullable=True)
    is_active = Column(Integer, default=1)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    driver = relationship("User")


class DriverCollection(Base):
    __tablename__ = "driver_collections"
    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(String(50), unique=True, index=True, nullable=False)  # COL-000001
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    driver_name = Column(String(100), nullable=False)
    driver_employee_id = Column(String(50), nullable=True)
    dustbin_id = Column(Integer, ForeignKey("dustbins.id"), nullable=False)
    dustbin_code = Column(String(50), nullable=False)
    location = Column(String(200), nullable=True)
    waste_type = Column(String(50), nullable=True)        # e.g. Dry Recyclable / Organic / Mixed
    status = Column(String(20), default="COMPLETED")      # COMPLETED / PENDING
    points = Column(Integer, default=10)
    collected_at = Column(DateTime(timezone=True), server_default=func.now())
    dustbin = relationship("Dustbin", backref="driver_collections")
    driver = relationship("User", backref="driver_collections")


class CollectionTask(Base):
    """Auto-assigned collection task for a full dustbin.

    State machine:
        PENDING_ASSIGNMENT -> ASSIGNED -> ACCEPTED -> ON_ROUTE -> ARRIVED
        -> COLLECTING -> COMPLETED
    (PENDING_ASSIGNMENT is held while no available driver exists; the system
    retries automatically whenever a driver frees up or a new live fix arrives.)
    """
    __tablename__ = "collection_tasks"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(50), unique=True, index=True, nullable=False)   # T-000001
    dustbin_id = Column(Integer, ForeignKey("dustbins.id"), nullable=False, index=True)
    dustbin_code = Column(String(50), nullable=False)
    fill_level = Column(Float, default=0.0)
    location = Column(String(200), nullable=True)
    zone = Column(String(100), nullable=True)
    priority = Column(String(20), default="HIGH")            # HIGH / MEDIUM / LOW
    assignment_mode = Column(String(20), default="AUTOMATIC") # AUTOMATIC / MANUAL / NONE
    status = Column(String(30), default="PENDING_ASSIGNMENT")
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    driver_name = Column(String(100), nullable=True)
    driver_employee_id = Column(String(50), nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    arrived_at = Column(DateTime(timezone=True), nullable=True)
    collecting_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    distance_km = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    dustbin = relationship("Dustbin")
    driver = relationship("User")
