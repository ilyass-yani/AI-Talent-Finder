#!/usr/bin/env python3
"""
Test client to simulate frontend API calls
"""

import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_no_auth():
    """Test without authentication"""
    print("=" * 60)
    print("TEST 1: Without Authentication")
    print("=" * 60)
    response = requests.get(f"{BASE_URL}/candidates/me/profile")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_with_token():
    """Test with valid token"""
    print("=" * 60)
    print("TEST 2: Login and Get Profile")
    print("=" * 60)
    
    # Step 1: Login
    login_payload = {
        "email": "alice@test.com",
        "password": "password123"
    }
    login_response = requests.post(f"{BASE_URL}/auth/login", json=login_payload)
    print(f"Login Status: {login_response.status_code}")
    login_data = login_response.json()
    
    if login_response.status_code != 200:
        print(f"Login failed: {login_data}")
        return
    
    token = login_data["access_token"]
    print(f"✅ Got token: {token[:50]}...")
    print()
    
    # Step 2: Try to get profile WITHOUT token
    print("TEST 2a: Profile WITHOUT token:")
    response = requests.get(f"{BASE_URL}/candidates/me/profile")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")
    print()
    
    # Step 3: Try to get profile WITH token
    print("TEST 2b: Profile WITH token:")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/candidates/me/profile", headers=headers)
    print(f"  Status: {response.status_code}")
    print(f"  Response: {json.dumps(response.json(), indent=2)[:200]}...")
    print()

if __name__ == "__main__":
    print("\n🧪 TESTING API ENDPOINTS\n")
    test_no_auth()
    test_with_token()
    print("\n✅ Tests complete!\n")
