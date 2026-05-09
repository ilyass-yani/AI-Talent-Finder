#!/usr/bin/env python3
"""
Run simple chatbot scenarios against deployed or local API for QA.
Usage:
  API_BASE_URL=https://... PYTHONPATH=. python3 backend/scripts/chatbot_scenarios.py
"""
import os
import requests
import json

BASE = os.getenv('API_BASE_URL', 'http://127.0.0.1:8000')
HEADERS = {'Content-Type': 'application/json'}

scenarios = [
    {
        'name': 'Explain candidate match (sample)',
        'endpoint': '/api/chat/explain',
        'method': 'post',
        'payload': {
            'candidate_id': 1,
            'criteria_id': 1,
        }
    },
    {
        'name': 'Generate ideal profile (sample)',
        'endpoint': '/api/matching/generate',
        'method': 'post',
        'payload': {
            'title': 'Senior Python Developer',
            'description': 'Looking for backend engineer with FastAPI and ML experience.'
        }
    }
]

print(f"Running chatbot scenarios against {BASE}")
for s in scenarios:
    url = BASE.rstrip('/') + s['endpoint']
    print('\n---')
    print('Scenario:', s['name'])
    try:
        if s['method'].lower() == 'post':
            r = requests.post(url, headers=HEADERS, json=s['payload'], timeout=30)
        else:
            r = requests.get(url, headers=HEADERS, timeout=30)
        print('Status:', r.status_code)
        try:
            print('Response:', json.dumps(r.json(), indent=2, ensure_ascii=False)[:2000])
        except Exception:
            print('Response text:', r.text[:2000])
    except Exception as e:
        print('Error calling endpoint:', e)

print('\nDone.')
