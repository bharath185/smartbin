"""Seed role-based users for the SmartBin demo (customer / driver / municipality).
Run once:  python -m app.seed_users  (from the backend directory with venv active)
Uses the same bcrypt hashing and will skip accounts that already exist.
"""
from passlib.context import CryptContext
from .database import SessionLocal, Base, engine
from .models import User
import bcrypt

Base.metadata.create_all(bind=engine)


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

SEED_USERS = [
    # (role, full_name, mobile, email, password, city_or_area, employee_id, vehicle, area, license, dept, designation, municipality_name, status)
    ("customer", "Riya Sharma", "9820012345", "customer@demo.com", "demo1234", "Sector 12, Green City", None, None, None, None, None, None, None, "active"),
    ("driver", "Aarav Mehta", "9820034567", "driver@demo.com", "demo1234", None, "EMP1000", "MH-12-AB-1234", "Sector 12, Green City", "DL-MH-2019-88451", None, None, None, "verified"),
    ("municipality", "Smart City Office", "9820054321", "municipal@demo.com", "demo1234", None, "MUN-001", None, None, None, "Environment", "Municipal Commissioner", "Green City Municipal Corporation", "approved"),
    ("driver", "Vikram Singh", "9820098765", "driver.pending@demo.com", "demo1234", None, "EMP1001", "MH-12-CD-5678", "Sector 21, Green City", "DL-MH-2021-12904", None, None, None, "pending"),
    ("municipality", "North Zone Office", "9820077777", "northzone@demo.com", "demo1234", None, "MUN-002", None, None, None, "Sanitation", "Zonal Officer", "North Zone Municipal Council", "pending"),
    ("customer", "Aditya Joshi", "9820111222", "customer2@demo.com", "demo1234", "Sector 21, Green City", None, None, None, None, None, None, None, "active"),
    ("customer", "Meera Nair", "9820133333", "customer3@demo.com", "demo1234", "Sector 5, Green City", None, None, None, None, None, None, None, "suspended"),
]


def main():
    db = SessionLocal()
    added = 0
    for row in SEED_USERS:
        (
            role, full_name, mobile, email, password, city_or_area, employee_id,
            vehicle, area, license, dept, designation, municipality_name, status,
        ) = row
        exists = db.query(User).filter(User.email == email).first()
        if exists:
            continue
        db.add(User(
            role=role,
            full_name=full_name,
            mobile=mobile,
            email=email,
            hashed_password=_hash(password),
            city_or_area=city_or_area,
            employee_id=employee_id,
            vehicle_number=vehicle,
            assigned_area=area,
            driving_license=license,
            department=dept,
            designation=designation,
            municipality_name=municipality_name,
            status=status,
        ))
        added += 1
    db.commit()
    db.close()
    print(f"Seeded {added} role-based users.")


if __name__ == "__main__":
    main()