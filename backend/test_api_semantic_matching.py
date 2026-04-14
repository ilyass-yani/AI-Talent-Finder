#!/usr/bin/env python3
"""
Quick API test examples for semantic matching
Run this after starting the FastAPI server
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api/matching"

def print_response(title: str, response: requests.Response):
    """Pretty print API response"""
    print(f"\n{'='*60}")
    print(f"📍 {title}")
    print(f"{'='*60}")
    print(f"Status: {response.status_code}")
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print(response.text)


def test_create_criteria():
    """Test: Create job criteria"""
    print("\n🧪 TEST 1: Create Job Criteria")
    
    payload = {
        "title": "Senior Python Developer",
        "description": "We need an experienced Python developer with Django and PostgreSQL expertise",
        "mode": "search",
        "required_skills": [
            {"name": "Python", "weight": 100},
            {"name": "Django", "weight": 80},
            {"name": "PostgreSQL", "weight": 70},
            {"name": "REST API", "weight": 60},
            {"name": "Docker", "weight": 50}
        ]
    }
    
    response = requests.post(f"{BASE_URL}/criteria", json=payload)
    print_response("Create Job Criteria", response)
    
    if response.status_code == 200:
        criteria_id = response.json().get("id")
        return criteria_id
    return None


def test_search_candidates(criteria_id: int):
    """Test: Search candidates matching criteria"""
    print("\n🧪 TEST 2: Search Candidates (Semantic Matching)")
    
    if not criteria_id:
        print("⚠️  Skip: No criteria_id from previous test")
        return
    
    response = requests.post(f"{BASE_URL}/search/{criteria_id}")
    print_response("Search Candidates", response)


def test_generate_profile():
    """Test: Generate ideal profile from job description"""
    print("\n🧪 TEST 3: Generate Ideal Profile")
    
    payload = {
        "job_title": "Full Stack Engineer",
        "description": """
        Looking for a Full Stack Engineer who can:
        - Build scalable Python backends with Django/FastAPI
        - Create responsive frontend with React or Vue
        - Manage PostgreSQL databases
        - Deploy on AWS/Docker
        - Work with microservices architecture
        Required: 3+ years experience, Agile methodology
        """
    }
    
    response = requests.post(f"{BASE_URL}/generate-profile", json=payload)
    print_response("Generate Profile", response)


def test_generate_and_match():
    """Test: Generate profile and match against candidates"""
    print("\n🧪 TEST 4: Generate & Match (Complete Workflow)")
    
    payload = {
        "job_title": "Full Stack Engineer",
        "description": """
        We need a Full Stack Engineer who is strong in:
        - Python/Django backend development
        - React frontend
        - PostgreSQL and Redis
        - Cloud deployment (AWS preferred)
        """
    }
    
    response = requests.post(f"{BASE_URL}/generate-and-match", json=payload)
    print_response("Generate & Match", response)


def test_semantic_similarity():
    """Test semantic similarity endpoint (if available)"""
    print("\n🧪 TEST 5: Semantic Similarity (if endpoint exists)")
    
    payload = {
        "skill1": "Python",
        "skill2": "Django",
        "threshold": 0.6
    }
    
    # This endpoint might not exist yet - just try
    response = requests.post(f"{BASE_URL}/similarity", json=payload)
    if response.status_code != 404:
        print_response("Semantic Similarity", response)
    else:
        print("⚠️  Endpoint not available (can be created later)")


def main():
    """Run all test scenarios"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  🚀 API Tests - Semantic Matching".center(58) + "║")
    print("║" + "  all-MiniLM-L6-v2 Integration".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    print("✅ Before running these tests:")
    print("   1. pip install -r requirements.txt")
    print("   2. python -m uvicorn app.main:app --reload")
    print("   3. Wait for server to start on http://localhost:8000")
    print()
    
    try:
        # Test API connectivity
        print("🔍 Checking API connectivity...")
        response = requests.get("http://localhost:8000", timeout=2)
        print("   ✓ API is reachable")
    except Exception as e:
        print(f"   ✗ API is not reachable: {e}")
        print("\n   Make sure the FastAPI server is running:")
        print("   python -m uvicorn app.main:app --reload")
        return
    
    try:
        # Run tests
        criteria_id = test_create_criteria()
        test_search_candidates(criteria_id)
        test_generate_profile()
        test_generate_and_match()
        test_semantic_similarity()
        
        print("\n")
        print("=" * 60)
        print("✅ Test Suite Completed!")
        print("=" * 60)
        print("\n📊 Next Steps:")
        print("   1. Check the responses above for correctness")
        print("   2. Create test data with actual candidates")
        print("   3. Compare scoring before/after semantic matching")
        print("   4. Adjust threshold if needed: backend/app/api/matching.py")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


# ============================================================================
# CURL Examples - Use if you prefer command line
# ============================================================================
"""
# 1. Create criteria
curl -X POST http://localhost:8000/api/matching/criteria \\
  -H "Content-Type: application/json" \\
  -d '{
    "title": "Senior Python Developer",
    "description": "Expert needed in Python, Django, PostgreSQL",
    "mode": "search",
    "required_skills": [
      {"name": "Python", "weight": 100},
      {"name": "Django", "weight": 80},
      {"name": "PostgreSQL", "weight": 70}
    ]
  }'

# 2. Search candidates (replace 1 with criteria_id)
curl -X POST http://localhost:8000/api/matching/search/1

# 3. Generate and match
curl -X POST http://localhost:8000/api/matching/generate-and-match \\
  -H "Content-Type: application/json" \\
  -d '{
    "job_title": "Senior Python Developer",
    "description": "Besoin expert Python, Django, PostgreSQL, Docker"
  }'
"""
