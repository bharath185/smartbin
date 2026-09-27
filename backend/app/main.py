from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from .database import engine, Base
from .routers import auth, dashboard, dustbins, employees, leaderboard, complaints, collections, locations, tasks

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

@app.get("/")
def health_check():
    return {"message": "Smart Dustbin API is running"}