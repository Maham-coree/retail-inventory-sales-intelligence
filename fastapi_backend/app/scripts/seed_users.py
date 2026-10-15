"""Idempotently create the three documented local demo users."""

from sqlalchemy import text

from ..database import SessionLocal
from ..security import hash_password

DEMO_USERS = (
    ("admin", "Admin@123", "admin", None),
    ("manager", "Manager@123", "manager", 1),
    ("cashier", "Cashier@123", "cashier", 2),
)


def seed_users() -> int:
    created = 0
    with SessionLocal.begin() as db:
        for username, password, role, employee_id in DEMO_USERS:
            result = db.execute(
                text(
                    "INSERT INTO retail.app_users "
                    "(username, password_hash, role, employee_id) "
                    "VALUES (:username, :password_hash, :role, :employee_id) "
                    "ON CONFLICT (username) DO NOTHING"
                ),
                {
                    "username": username,
                    "password_hash": hash_password(password),
                    "role": role,
                    "employee_id": employee_id,
                },
            )
            created += result.rowcount
    return created


if __name__ == "__main__":
    count = seed_users()
    print(f"Seed completed; created {count} missing account(s).")
