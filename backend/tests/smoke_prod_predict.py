#!/usr/bin/env python3
"""Simple smoke test for production /api/matching/{id}/predict endpoint.

Usage:
  PROD_URL=https://... python backend/tests/smoke_prod_predict.py [criteria_id]
"""
import os
import sys
import json
from urllib import request as urlrequest, error as urlerror


def main():
    base = os.getenv("PROD_URL", "http://localhost:8000")
    criteria_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    top_k = os.getenv("TOP_K", "10")
    auth_token = os.getenv("AUTH_TOKEN", "").strip()

    url = f"{base.rstrip('/')}/api/matching/{criteria_id}/predict?top_k={top_k}"
    print("Calling:", url)
    try:
        req = urlrequest.Request(url, method='POST')
        if auth_token:
            req.add_header('Authorization', f'Bearer {auth_token}')
        with urlrequest.urlopen(req, timeout=10) as resp:
            status = resp.getcode()
            body = resp.read().decode('utf-8')
            print('Status:', status)
            try:
                print(json.loads(body))
            except Exception:
                print(body)
        return 0
    except urlerror.HTTPError as e:
        print('Status:', e.code)
        try:
            print(e.read().decode('utf-8'))
        except Exception:
            print(e)
        return 0
    except Exception as e:
        print("Request failed:", e)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
