#!/usr/bin/env python3
"""
Seed script to create test users for development
Run: python seed_test_users.py
"""

import sys
sys.path.insert(0, '.')

from app.core.database import SessionLocal, engine
from app.models.models import Base, User, UserRole
from app.core.security import get_password_hash

def seed_users():
    """Create test users"""
    db = SessionLocal()
    
    # Create tables if not exist
    Base.metadata.create_all(bind=engine)
    
    # Test users
    test_users = [
        {
            "email": "alice@test.com",
            "password": "password123",
            "full_name": "Alice Johnson",
            "role": UserRole.candidate
        },
        {
            "email": "bob@test.com",
            "password": "password123",
            "full_name": "Bob Smith",
            "role": UserRole.recruiter
        },
        {
            "email": "alice@example.com",
            "password": "pass123",
            "full_name": "Alice Example",
            "role": UserRole.candidate
        }
    ]
    
    for user_data in test_users:
        # Check if user already exists
        existing = db.query(User).filter(User.email == user_data["email"]).first()
        if existing:
            print(f"✓ User {user_data['email']} already exists")
            continue
        
        # Create new user
        db_user = User(
            email=user_data["email"],
            hashed_password=get_password_hash(user_data["password"]),
            full_name=user_data["full_name"],
            role=user_data["role"]
        )
        db.add(db_user)
        print(f"+ Created user: {user_data['email']} ({user_data['role']})")
    
    db.commit()
    db.close()
    print("\n✅ Seed complete!")

if __name__ == "__main__":
    seed_users()
