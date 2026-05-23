"""
Basic IA integration smoke tests that call deployed endpoints.
Run with: API_BASE_URL=https://... python3 backend/tests/ia_integration_tests.py
"""
import os
import requests

BASE = os.getenv('API_BASE_URL', 'http://127.0.0.1:8000')


def expect_ok(path):
    url = BASE.rstrip('/') + path
    print('Checking', url)
    try:
        r = requests.get(url, timeout=15)
        print('->', r.status_code)
        return r.status_code < 400
    except Exception as e:
        print('-> error', e)
        return False


if __name__ == '__main__':
    ok = True
    ok &= expect_ok('/docs')
    ok &= expect_ok('/api/candidates?skip=0&limit=1')
    ok &= expect_ok('/api/favorites?skip=0&limit=1')

    if ok:
        print('\nIA integration basic checks: OK')
    else:
        print('\nIA integration basic checks: FAIL')
        exit(2)
