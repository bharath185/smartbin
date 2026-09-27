from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from .database import engine, Base
from .routers import auth, dashboard, dustbins, employees, leaderboard, complaints, collections, locations, tasks, iot

# Create all tables on startup
Base.metadata.create_all(bind=engine)

# Lightweight migrations for existing databases
def _migrate():
    insp = inspect(engine)

    def cols(table):
        return {c["name"] for c in insp.get_columns(table)} if table in insp.get_table_names() else set()

    with engine.begin() as conn:
        # complaints: feedback / images columns
        if "complaints" in insp.get_table_names():
            cc = cols("complaints")
            if "feedback" not in cc:
                conn.execute(text("ALTER TABLE complaints ADD COLUMN feedback TEXT"))
            if "images" not in cc:
                conn.execute(text("ALTER TABLE complaints ADD COLUMN images TEXT"))
        # dustbins: optional coordinate columns (used for route drawing on the map)
        if "dustbins" in insp.get_table_names():
            dc = cols("dustbins")
            if "latitude" not in dc:
                conn.execute(text("ALTER TABLE dustbins ADD COLUMN latitude FLOAT"))
            if "longitude" not in dc:
                conn.execute(text("ALTER TABLE dustbins ADD COLUMN longitude FLOAT"))
        # users: driver-management columns
        if "users" in insp.get_table_names():
            uc = cols("users")
            extra = {
                "address": "VARCHAR(300)",
                "vehicle_type": "VARCHAR(50)",
                "assigned_route": "VARCHAR(100)",
                "license_number": "VARCHAR(100)",
                "approved_date": "DATETIME",
                "approved_by": "VARCHAR(100)",
                "rejection_reason": "VARCHAR(300)",
                "last_active": "DATETIME",
                "updated_at": "DATETIME",
            }
            for name, ddl in extra.items():
                if name not in uc:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))
            # Normalize driver statuses: verified -> active (legacy)
            conn.execute(text("UPDATE users SET status = 'active' WHERE role = 'driver' AND status = 'verified'"))

_migrate()

def _auto_seed():
    try:
        from .database import SessionLocal
        from .models import Dustbin, Employee, User
        import bcrypt
        with SessionLocal() as db:
            if db.query(Employee).count() == 0:
                def _h(pw): return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
                db.add(Employee(employee_id="EMP001", name="Alice Johnson", email="alice@smartbin.com", phone="9876543210", hashed_password=_h("password123"), role="admin"))
                db.add(User(role="driver", full_name="Demo Driver", email="driver@demo.com", mobile="9876543220", hashed_password=_h("demo1234"), status="active", vehicle_number="KA-01-AB-1234", vehicle_type="Truck", assigned_route="Route North"))
                db.add(User(role="customer", full_name="Demo Customer", email="customer@demo.com", mobile="9876543221", hashed_password=_h("demo1234"), status="active"))
                bins = [
                    ("DB001", "Main Lobby", 45.0, "EMPTY", 12.9716, 77.5946),
                    ("DB002", "Cafeteria", 92.0, "FILLED", 12.9720, 77.5950),
                    ("DB003", "Parking Lot A", 15.0, "EMPTY", 12.9710, 77.5930),
                    ("DB004", "Office Floor 2", 88.0, "FILLED", 12.9730, 77.5960),
                    ("DB005", "Library", 5.0, "EMPTY", 12.9715, 77.5955),
                    ("DB006", "Gym", 78.0, "READY", 12.9725, 77.5940),
                    ("DB007", "Reception", 95.0, "READY", 12.9705, 77.5945),
                    ("DB008", "Workshop", 30.0, "EMPTY", 12.9735, 77.5935),
                ]
                for bid, loc, fill, st, lat, lng in bins:
                    db.add(Dustbin(dustbin_id=bid, location=loc, fill_level=fill, status=st, latitude=lat, longitude=lng))
                db.commit()
    except Exception as e:
        pass

_auto_seed()

app = FastAPI(title="Smart Dustbin Management", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,        prefix="/auth",        tags=["Auth"])
app.include_router(dashboard.router,    prefix="/dashboard",   tags=["Dashboard"])
app.include_router(dustbins.router,     prefix="/dustbins",    tags=["Dustbins"])
app.include_router(employees.router,    prefix="/employees",   tags=["Employees"])
app.include_router(leaderboard.router,  prefix="/leaderboard", tags=["Leaderboard"])
app.include_router(complaints.router,   prefix="/complaints",  tags=["Complaints"])
app.include_router(collections.router,  prefix="/collections", tags=["Collections"])
app.include_router(locations.router,    prefix="/drivers",     tags=["Driver Location"])
app.include_router(tasks.router,        prefix="/tasks",       tags=["Collection Tasks"])
app.include_router(iot.router,          prefix="/iot",         tags=["IoT Devices & Telemetry"])

# Also mount under /api prefix for Vercel serverless functions
app.include_router(auth.router,        prefix="/api/auth",        include_in_schema=False)
app.include_router(dashboard.router,    prefix="/api/dashboard",   include_in_schema=False)
app.include_router(dustbins.router,     prefix="/api/dustbins",    include_in_schema=False)
app.include_router(employees.router,    prefix="/api/employees",   include_in_schema=False)
app.include_router(leaderboard.router,  prefix="/api/leaderboard", include_in_schema=False)
app.include_router(complaints.router,   prefix="/api/complaints",  include_in_schema=False)
app.include_router(collections.router,  prefix="/api/collections", include_in_schema=False)
app.include_router(locations.router,    prefix="/api/drivers",     include_in_schema=False)
app.include_router(tasks.router,        prefix="/api/tasks",       include_in_schema=False)
app.include_router(iot.router,          prefix="/api/iot",         include_in_schema=False)

@app.get("/")
@app.get("/api")
@app.get("/api/")
def health_check():
    return {"message": "Smart Dustbin API is running on Vercel", "status": "online"}