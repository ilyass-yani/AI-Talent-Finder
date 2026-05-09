#!/usr/bin/env python3
"""
Minimal seed script to create test data for recruiter visibility testing
Adds: 1 recruiter + 1 candidate with profile + 1 favorite link

Run: PYTHONPATH=. python seed_minimal_recruiter_test.py
"""

import sys
sys.path.insert(0, '.')

from app.core.database import SessionLocal, engine
from app.models.models import Base, User, UserRole, Candidate, Favorite
from app.core.security import get_password_hash
import uuid
from pathlib import Path

def seed_minimal():
    """Create minimal test data"""
    db = SessionLocal()
    
    # Create tables if not exist
    Base.metadata.create_all(bind=engine)
    
    # Clear existing data (for clean reset)
    db.query(Favorite).delete()
    db.query(Candidate).delete()
    db.query(User).delete()
    db.commit()
    
    print("✓ Cleared existing data")
    
    # 1. Create recruiter user
    recruiter = User(
        email="recruiter@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Test Recruiter",
        role=UserRole.recruiter
    )
    db.add(recruiter)
    db.flush()
    recruiter_id = recruiter.id
    print(f"+ Created recruiter: recruiter@test.com (ID: {recruiter_id})")
    
    # 2. Create candidate user
    candidate_user = User(
        email="candidate@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="John Developer",
        role=UserRole.candidate
    )
    db.add(candidate_user)
    db.flush()
    candidate_user_id = candidate_user.id
    print(f"+ Created candidate user: candidate@test.com (ID: {candidate_user_id})")
    
    # 3. Create candidate profile with all signals
    synthetic_cv_text = """
John Developer
john.developer@gmail.com
+33 6 12 34 56 78

Senior Full-Stack Developer | 8 years experience

EXPERIENCE:
- Senior Developer at TechCorp (2020-present): Led team of 5 engineers
- Full-Stack Developer at StartupXYZ (2018-2020): Built microservices architecture
- Junior Developer at WebAgency (2015-2018): Developed web applications

SKILLS:
- Languages: Python, JavaScript, TypeScript, SQL
- Frameworks: FastAPI, React, Django, Next.js
- Databases: PostgreSQL, MongoDB, Redis
- Tools: Docker, Kubernetes, AWS, Git

EDUCATION:
- Master's in Computer Science, University of Paris (2015)
- Bachelor's in Software Engineering, University of Lyon (2013)

CERTIFICATIONS:
- AWS Solutions Architect Associate
- Kubernetes Certified Associate Application Developer

LANGUAGES:
- French (Native)
- English (Fluent)
- Spanish (Intermediate)

PROJECTS:
- AI-powered recruiting platform (Python, FastAPI, React)
- Real-time analytics dashboard (Node.js, Vue.js)
"""
    
    candidate = Candidate(
        user_id=candidate_user_id,
        full_name="John Developer",
        email="john.developer@gmail.com",
        phone="+33 6 12 34 56 78",
        linkedin_url="https://linkedin.com/in/john-developer",
        github_url="https://github.com/jdeveloper",
        cv_path="uploads/cvs/test_candidate.pdf",
        raw_text=synthetic_cv_text,
        extracted_name="John Developer",
        extracted_emails="john.developer@gmail.com",
        extracted_phones="+33 6 12 34 56 78",
        extracted_job_titles='["Senior Full-Stack Developer", "Full-Stack Developer", "Junior Developer"]',
        extracted_companies='["TechCorp", "StartupXYZ", "WebAgency"]',
        extracted_education='["Master\'s in Computer Science", "Bachelor\'s in Software Engineering"]',
        extraction_quality_score=0.92,
        is_fully_extracted=True,
        ner_extraction_data='{"languages": ["French", "English", "Spanish"], "experiences": ["Senior Developer", "Full-Stack Developer"], "projects": ["AI-powered recruiting platform", "Real-time analytics dashboard"], "certifications": ["AWS Solutions Architect Associate"], "github_urls": ["https://github.com/jdeveloper"], "portfolio_urls": [], "linkedin_urls": ["https://linkedin.com/in/john-developer"]}'
    )
    db.add(candidate)
    db.flush()
    candidate_id = candidate.id
    print(f"+ Created candidate profile: John Developer (ID: {candidate_id})")
    
    # 4. Create favorite link (recruiter favorites candidate)
    favorite = Favorite(
        recruiter_id=recruiter_id,
        candidate_id=candidate_id
    )
    db.add(favorite)
    db.commit()
    print(f"+ Created favorite link: Recruiter {recruiter_id} -> Candidate {candidate_id}")
    
    db.close()
    print("\n✅ Seed complete!")
    print("\n📝 TEST CREDENTIALS:")
    print("═" * 50)
    print("RECRUITER:")
    print("  Email: recruiter@test.com")
    print("  Password: password123")
    print("\nCANDIDATE:")
    print("  Email: candidate@test.com")
    print("  Password: password123")
    print("═" * 50)
    print("\n🎯 NEXT STEPS:")
    print("1. Login as recruiter@test.com")
    print("2. Go to /recruiter/shortlist → should see 'John Developer'")
    print("3. Go to /candidates → should see 'John Developer'")
    print("4. Login as candidate@test.com")
    print("5. Go to /candidate/dashboard → should see your profile")

if __name__ == "__main__":
    seed_minimal()
