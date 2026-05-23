#!/usr/bin/env python3
"""Simple script to POST a test job to production generate-and-match endpoint."""
import json
import sys
import requests

URL = "https://ai-talent-finder-production-ed09.up.railway.app/api/matching/generate-and-match"
payload = {
    "job_title": "Auto: Data Scientist",
    "description": "Looking for Python, ML, Docker"
}

def main():
    try:
        resp = requests.post(URL, json=payload, timeout=30)
    except Exception as e:
        print(f"ERROR: request failed: {e}")
        sys.exit(2)

    print(f"STATUS: {resp.status_code}")
    try:
        data = resp.json()
        print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
    except Exception:
        print(resp.text[:2000])


if __name__ == '__main__':
    main()
