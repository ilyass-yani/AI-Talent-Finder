#!/usr/bin/env python3
"""
End-to-end test simulating the frontend workflow
"""

import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000/api"

# Step 1: Create a test PDF
test_pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Test CV) Tj ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000244 00000 n
0000000330 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
424
%%EOF"""

pdf_path = Path("/tmp/test_cv.pdf")
pdf_path.write_bytes(test_pdf_content)
print(f"✓ Created test PDF: {pdf_path}")

# Step 2: Login
print("\n1️⃣ LOGIN")
login_resp = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "alice@test.com",
    "password": "password123"
})
print(f"   Status: {login_resp.status_code}")
if login_resp.status_code == 200:
    login_data = login_resp.json()
    token = login_data['access_token']
    print(f"   Token: {token[:50]}...")
else:
    print(f"   Error: {login_resp.json()}")
    exit(1)

headers = {"Authorization": f"Bearer {token}"}

# Step 3: Check profile before upload
print("\n2️⃣ GET PROFILE (before upload)")
profile_resp = requests.get(f"{BASE_URL}/candidates/me/profile", headers=headers)
print(f"   Status: {profile_resp.status_code}")
print(f"   Response: {profile_resp.json()['detail']}")

# Step 4: Upload CV
print("\n3️⃣ UPLOAD CV")
with open(pdf_path, 'rb') as f:
    files = {'file': f}
    upload_resp = requests.post(f"{BASE_URL}/candidates/upload", headers=headers, files=files)

print(f"   Status: {upload_resp.status_code}")
if upload_resp.status_code == 200:
    upload_data = upload_resp.json()
    print(f"   ✅ Upload successful!")
    print(f"   Candidate ID: {upload_data.get('candidate_id')}")
    print(f"   Quality Score: {upload_data.get('extraction', {}).get('quality_score')}")
else:
    print(f"   ❌ Upload failed!")
    print(f"   Response: {upload_resp.text[:200]}")

# Step 5: Check profile after upload
print("\n4️⃣ GET PROFILE (after upload)")
profile_resp = requests.get(f"{BASE_URL}/candidates/me/profile", headers=headers)
print(f"   Status: {profile_resp.status_code}")
if profile_resp.status_code == 200:
    data = profile_resp.json()
    print(f"   ✅ Profile found!")
    print(f"   Name: {data.get('full_name')}")
    print(f"   Email: {data.get('email')}")
    print(f"   Extraction Quality: {data.get('extraction_quality_score')}")
else:
    print(f"   Error: {profile_resp.json()}")

print("\n✅ Test complete!")
