#!/usr/bin/env python3
import requests, json
BASE='https://ai-talent-finder-backend-production.up.railway.app'

# Login recruiter
r=requests.post(BASE+'/api/auth/login', json={'email':'recruiter@test.com','password':'password123'}, timeout=15)
if r.status_code!=200:
    print('Login failed', r.status_code, r.text)
    raise SystemExit(1)
token=r.json().get('access_token')
headers={'Authorization':f'Bearer {token}','Content-Type':'application/json'}

# Create criteria
payload={'title':'Senior Python Developer','description':'Looking for backend engineer with FastAPI and ML experience','required_skills':[{'name':'Python','weight':80},{'name':'FastAPI','weight':70},{'name':'Machine Learning','weight':60}]}
r2=requests.post(BASE+'/api/criteria', headers=headers, json=payload, timeout=30)
print('create criteria', r2.status_code)
print(r2.text[:1000])

if r2.status_code==201:
    cid=r2.json().get('id')
    print('criteria id', cid)
    # generate and match
    r3=requests.post(BASE+'/api/matching/generate-and-match', headers=headers, json={'job_title':'Senior Python Developer','description':'Looking for backend engineer with FastAPI and ML experience'}, timeout=60)
    print('generate-and-match', r3.status_code)
    try:
        print(json.dumps(r3.json(), indent=2)[:2000])
    except Exception:
        print(r3.text[:2000])
    # match explanation
    r4=requests.post(BASE+'/api/matching/match-explanation', headers=headers, json={'candidate_id':1,'job_criteria_id':cid}, timeout=30)
    print('match-explanation', r4.status_code)
    try:
        print(json.dumps(r4.json(), indent=2)[:2000])
    except Exception:
        print(r4.text[:2000])
else:
    print('Criteria creation failed; status', r2.status_code)
