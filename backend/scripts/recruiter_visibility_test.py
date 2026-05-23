from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, engine

# Reset DB
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)

# Register candidate
reg_c = client.post('/api/auth/register', json={
    'email':'cand1@example.com',
    'password':'password123',
    'full_name':'Cand One',
    'role':'candidate'
})
print('reg candidate', reg_c.status_code)
login_c = client.post('/api/auth/login', json={'email':'cand1@example.com','password':'password123'})
print('login candidate', login_c.status_code)
c_token = login_c.json().get('access_token')

# Create candidate profile via POST /api/candidates/
create_resp = client.post('/api/candidates/', json={'full_name':'Cand One','email':'cand1@example.com','raw_text':'This is my CV text'}, headers={'Authorization':f'Bearer {c_token}'})
print('create candidate profile', create_resp.status_code)
try:
    print(create_resp.json())
except Exception:
    print(create_resp.text[:200])

# Register recruiter
reg_r = client.post('/api/auth/register', json={'email':'rec1@example.com','password':'password123','full_name':'Recruiter One','role':'recruiter'})
print('reg recruiter', reg_r.status_code)
login_r = client.post('/api/auth/login', json={'email':'rec1@example.com','password':'password123'})
print('login recruiter', login_r.status_code)
r_token = login_r.json().get('access_token')

# Get candidates as recruiter
resp = client.get('/api/candidates/', headers={'Authorization':f'Bearer {r_token}'})
print('get candidates', resp.status_code)
print(resp.json())
