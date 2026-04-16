#!/usr/bin/env python3
"""
Migration script to link existing Candidates to Users by email
Run this once to fix backwards compatibility
"""

import sys
sys.path.insert(0, '.')

from app.core.database import SessionLocal
from app.models.models import User, Candidate

def migrate_candidates():
    """Link candidates to users by matching email"""
    db = SessionLocal()
    
    # Find all candidates with NULL user_id
    orphaned = db.query(Candidate).filter(Candidate.user_id == None).all()
    print(f"Found {len(orphaned)} candidates without user_id")
    
    updated_count = 0
    for candidate in orphaned:
        # Find matching user by email
        user = db.query(User).filter(User.email == candidate.email).first()
        if user:
            candidate.user_id = user.id
            updated_count += 1
            print(f"✓ Linked candidate {candidate.email} → user {user.id}")
        else:
            print(f"✗ No user found for candidate {candidate.email}")
    
    if updated_count > 0:
        db.commit()
        print(f"\n✅ Updated {updated_count} candidates")
    else:
        print("\nℹ️  No candidates to update")
    
    db.close()

if __name__ == "__main__":
    migrate_candidates()
