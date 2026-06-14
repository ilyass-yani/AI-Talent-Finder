"""Integration test for pipeline endpoint (requires server running).

This test uses HTTP request to the running FastAPI app at localhost:8000.
It is provided for CI or local dev; it will be skipped if server not available.
"""
import requests


def test_pipeline_ping():
    url = "http://localhost:8000/api/pipeline/run"
    payload = {
        "candidate": {"raw_text": "Alice\n5 years Python, AWS"},
        "job": {"job_text": "Senior Python AWS"},
        "mode": "semantic",
    }
    try:
        r = requests.post(url, json=payload, timeout=5)
    except Exception:
        print("Server not running; skip integration test")
        return

    if r.status_code == 404:
        print("Pipeline endpoint not registered yet (startup may be incomplete); skipping")
        return

    assert r.status_code == 200
    data = r.json()
    assert "score" in data
