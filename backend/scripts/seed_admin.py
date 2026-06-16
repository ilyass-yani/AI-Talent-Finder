#!/usr/bin/env python3
"""
Create or reset the default admin account.

Usage:
    cd backend
    python scripts/seed_admin.py
    python scripts/seed_admin.py --email admin@example.com --password SuperSecret42!
"""
import argparse
import sys
from pathlib import Path

# Ensure the backend package is importable from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.models import User, UserRole

DEFAULT_EMAIL = "admin@aitalentfinder.local"
DEFAULT_PASSWORD = "Admin1234!"
DEFAULT_FULL_NAME = "Super Admin"


def seed_admin(email: str, password: str, full_name: str) -> None:
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            existing.hashed_password = get_password_hash(password)
            existing.role = UserRole.admin
            existing.is_active = True
            db.commit()
            print(f"[seed_admin] Admin account updated: {email}")
        else:
            admin = User(
                email=email,
                hashed_password=get_password_hash(password),
                full_name=full_name,
                role=UserRole.admin,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"[seed_admin] Admin account created: {email} (id={admin.id})")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed default admin account")
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--full-name", default=DEFAULT_FULL_NAME)
    args = parser.parse_args()

    seed_admin(email=args.email, password=args.password, full_name=args.full_name)
