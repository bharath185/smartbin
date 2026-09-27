import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from app.database import SessionLocal, engine, Base
from app.models import Dustbin, Employee, UnloadLog, RewardTransaction, User
import bcrypt
from datetime import datetime, timedelta
import random

def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Seed dustbins
bins = [
    ("DB001", "Main Lobby",    45, "EMPTY"),
    ("DB002", "Cafeteria",     92, "FILLED"),
    ("DB003", "Parking Lot A", 15, "EMPTY"),
    ("DB004", "Office Floor 2",88, "FILLED"),
    ("DB005", "Library",        5, "EMPTY"),
    ("DB006", "Gym",           78, "READY"),
    ("DB007", "Reception",     95, "READY"),
    ("DB008", "Workshop",      30, "EMPTY"),
]
for bid, loc, fill, st in bins:
    if not db.query(Dustbin).filter(Dustbin.dustbin_id == bid).first():
        db.add(Dustbin(dustbin_id=bid, location=loc, fill_level=fill, status=st,
                       qr_code=f"SMARTBIN:{bid}:demo"))
        print(f"  + Dustbin {bid}")

# Seed employees (Municipality admin & officers)
emps = [
    ("EMP001", "Alice Johnson",  "alice@smartbin.com",  "9876543210", "admin"),
    ("EMP002", "Bob Kumar",      "bob@smartbin.com",    "9876543211", "employee"),
    ("EMP003", "Charlie Singh",  "charlie@smartbin.com","9876543212", "employee"),
    ("EMP004", "Diana Patel",    "diana@smartbin.com",  "9876543213", "employee"),
    ("EMP005", "Eve Sharma",     "eve@smartbin.com",    "9876543214", "employee"),
]
for eid, name, email, phone, role in emps:
    if not db.query(Employee).filter(Employee.employee_id == eid).first():
        db.add(Employee(employee_id=eid, name=name, email=email, phone=phone,
                        hashed_password=_hash("password123"), role=role,
                        reward_points=random.randint(20, 150)))
        print(f"  + Employee {name}")

# Seed Users (Demo Drivers and Customers)
users_seed = [
    ("driver", "Demo Driver", "9876543220", "driver@demo.com", "demo1234", "active", "Route North", "TRUCK-01", "Truck", "DL-9876543210"),
    ("customer", "Demo Customer", "9876543221", "customer@demo.com", "demo1234", "active", None, None, None, None),
]
for role, name, phone, email, pw, status, route, vnum, vtype, lic in users_seed:
    if not db.query(User).filter(User.email == email).first():
        db.add(User(
            role=role, full_name=name, mobile=phone, email=email,
            hashed_password=_hash(pw), status=status,
            assigned_route=route, vehicle_number=vnum, vehicle_type=vtype,
            license_number=lic, driving_license=lic
        ))
        print(f"  + User {name} ({role})")

db.commit()

# Seed some unload logs
employees_db = db.query(Employee).all()
dustbins_db = db.query(Dustbin).all()
for _ in range(25):
    emp = random.choice(employees_db)
    dustbin = random.choice(dustbins_db)
    ts = datetime.utcnow() - timedelta(days=random.randint(0, 6), hours=random.randint(0, 23))
    pts = 10
    log = UnloadLog(dustbin_id=dustbin.id, employee_id=emp.id, points_earned=pts, timestamp=ts)
    db.add(log)
    tx = RewardTransaction(employee_id=emp.id, points=pts, transaction_type="earned",
                           description=f"Unloaded {dustbin.dustbin_id}", timestamp=ts)
    db.add(tx)

db.commit()
db.close()
print("\nSeed data loaded successfully!")
